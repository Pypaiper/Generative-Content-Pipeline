# Copyright 2024 MIT Han Lab
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0 # upsample on the temporal dimension as well

from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from opensora.models.vae.utils import ChannelChunkConv3d

from ...models.nn.act import build_act
from ...models.nn.norm import build_norm
from ...models.nn.vo_ops import (
    chunked_interpolate,
    get_same_padding,
    pixel_shuffle_3d,
    pixel_unshuffle_3d,
    resize,
)
from ...utils import list_sum, val2list, val2tuple

__all__ = [
    "ConvLayer",
    "UpSampleLayer",
    "ConvPixelUnshuffleDownSampleLayer",
    "PixelUnshuffleChannelAveragingDownSampleLayer",
    "ConvPixelShuffleUpSampleLayer",
    "ChannelDuplicatingPixelShuffleUpSampleLayer",
    "LinearLayer",
    "IdentityLayer",
    "DSConv",
    "MBConv",
    "FusedMBConv",
    "ResBlock",
    "LiteMLA",
    "EfficientViTBlock",
    "ResidualBlock",
    "DAGBlock",
    "OpSequential",
]


#################################################################################
#                             Basic Layers                                      #
#################################################################################


class ConvLayer(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size=3,
        stride=1,
        dilation=1,
        groups=1,
        use_bias=False,
        dropout=0,
        norm="bn2d",
        act_func="relu",
        is_video=False,
        pad_mode_3d="constant",
    ):
        super().__init__()
        self.is_video = is_video

        if self.is_video:
            assert dilation == 1, "only support dilation=1 for 3d conv"
            assert kernel_size % 2 == 1, "only support odd kernel size for 3d conv"
            self.pad_mode_3d = pad_mode_3d  # 3d padding follows CausalConv3d by Hunyuan
            # padding = (
            #     kernel_size // 2,
            #     kernel_size // 2,
            #     kernel_size // 2,
            #     kernel_size // 2,
            #     kernel_size - 1,
            #     0,
            # )  # W, H, T
            # non-causal padding
            padding = (
                kernel_size // 2,
                kernel_size // 2,
                kernel_size // 2,
                kernel_size // 2,
                kernel_size // 2,
                kernel_size // 2,
            )
            self.padding = padding
            self.dropout = nn.Dropout3d(dropout, inplace=False) if dropout > 0 else None
            assert isinstance(stride, (int, tuple)), (
                "stride must be an integer or 3-tuple for 3d conv"
            )
            self.conv = (
                ChannelChunkConv3d(  # padding is handled by F.pad() in forward()
                    in_channels,
                    out_channels,
                    kernel_size=(kernel_size, kernel_size, kernel_size),
                    stride=(stride, stride, stride)
                    if isinstance(stride, int)
                    else stride,
                    groups=groups,
                    bias=use_bias,
                )
            )
        else:
            padding = get_same_padding(kernel_size)
            padding *= dilation
            self.dropout = nn.Dropout2d(dropout, inplace=False) if dropout > 0 else None
            self.conv = nn.Conv2d(
                in_channels,
                out_channels,
                kernel_size=(kernel_size, kernel_size),
                stride=(stride, stride),
                padding=padding,
                dilation=(dilation, dilation),
                groups=groups,
                bias=use_bias,
            )

        self.norm = build_norm(norm, num_features=out_channels)
        self.act = build_act(act_func)
        self.pad = F.pad

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.dropout is not None:
            x = self.dropout(x)
        if self.is_video:  # custom padding for 3d conv
            x = self.pad(
                x, self.padding, mode=self.pad_mode_3d
            )  # "constant" padding defaults to 0
        x = self.conv(x)
        if self.norm:
            x = self.norm(x)
        if self.act:
            x = self.act(x)
        return x


class UpSampleLayer(nn.Module):
    def __init__(
        self,
        mode="bicubic",
        size: Optional[int | tuple[int, int] | list[int]] = None,
        factor=2,
        align_corners=False,
    ):
        super().__init__()
        self.mode = mode
        self.size = val2list(size, 2) if size is not None else None
        self.factor = None if self.size is not None else factor
        self.align_corners = align_corners

    @torch.autocast(device_type="cuda", enabled=False)
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if (
            self.size is not None and tuple(x.shape[-2:]) == self.size
        ) or self.factor == 1:
            return x
        if x.dtype in [torch.float16, torch.bfloat16]:
            x = x.float()
        return resize(x, self.size, self.factor, self.mode, self.align_corners)


class ConvPixelUnshuffleDownSampleLayer(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int,
        factor: int,
    ):
        super().__init__()
        self.factor = factor
        out_ratio = factor**2
        assert out_channels % out_ratio == 0
        self.conv = ConvLayer(
            in_channels=in_channels,
            out_channels=out_channels // out_ratio,
            kernel_size=kernel_size,
            use_bias=True,
            norm=None,
            act_func=None,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv(x)
        x = F.pixel_unshuffle(x, self.factor)
        return x


class PixelUnshuffleChannelAveragingDownSampleLayer(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        factor: int,
        temporal_downsample: bool = False,  # temporal downsample for 5d input tensor
    ):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.factor = factor
        self.temporal_downsample = temporal_downsample

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() == 4:
            assert self.in_channels * self.factor**2 % self.out_channels == 0
            group_size = self.in_channels * self.factor**2 // self.out_channels
            x = F.pixel_unshuffle(x, self.factor)
            B, C, H, W = x.shape
            x = x.view(B, self.out_channels, group_size, H, W)
            x = x.mean(dim=2)
        elif x.dim() == 5:  # [B, C, T, H, W]
            _, _, T, _, _ = x.shape
            if self.temporal_downsample and T != 1:  # 3d pixel unshuffle
                x = pixel_unshuffle_3d(x, self.factor)
                assert self.in_channels * self.factor**3 % self.out_channels == 0
                group_size = self.in_channels * self.factor**3 // self.out_channels
            else:  # 2d pixel unshuffle
                x = x.permute(0, 2, 1, 3, 4)  # [B, T, C, H, W]
                x = F.pixel_unshuffle(x, self.factor)
                x = x.permute(0, 2, 1, 3, 4)  # [B, C, T, H, W]
                assert self.in_channels * self.factor**2 % self.out_channels == 0
                group_size = self.in_channels * self.factor**2 // self.out_channels
            B, C, T, H, W = x.shape
            x = x.view(B, self.out_channels, group_size, T, H, W)
            x = x.mean(dim=2)
        else:
            raise ValueError(f"Unsupported input dimension: {x.dim()}")
        return x

    def __repr__(self):
        return f"PixelUnshuffleChannelAveragingDownSampleLayer(in_channels={self.in_channels}, out_channels={self.out_channels}, factor={self.factor}), temporal_downsample={self.temporal_downsample}"


class ConvPixelShuffleUpSampleLayer(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int,
        factor: int,
    ):
        super().__init__()
        self.factor = factor
        out_ratio = factor**2
        self.conv = ConvLayer(
            in_channels=in_channels,
            out_channels=out_channels * out_ratio,
            kernel_size=kernel_size,
            use_bias=True,
            norm=None,
            act_func=None,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv(x)
        x = F.pixel_shuffle(x, self.factor)
        return x


class InterpolateConvUpSampleLayer(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int,
        factor: int,
        mode: str = "nearest",
        is_video: bool = False,
        temporal_upsample: bool = False,
    ) -> None:
        super().__init__()
        self.factor = factor
        self.mode = mode
        self.temporal_upsample = temporal_upsample
        self.conv = ConvLayer(
            in_channels=in_channels,
            out_channels=out_channels,
            kernel_size=kernel_size,
            use_bias=True,
            norm=None,
            act_func=None,
            is_video=is_video,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() == 4:
            x = F.interpolate(x, scale_factor=self.factor, mode=self.mode)
        elif x.dim() == 5:
            # [B, C, T, H, W] -> [B, C, T*factor, H*factor, W*factor]
            if (
                self.temporal_upsample and x.size(2) != 1
            ):  # temporal upsample for video input
                x = chunked_interpolate(
                    x,
                    scale_factor=[self.factor, self.factor, self.factor],
                    mode=self.mode,
                )
            else:
                x = chunked_interpolate(
                    x, scale_factor=[1, self.factor, self.factor], mode=self.mode
                )
        x = self.conv(x)
        return x

    def __repr__(self):
        return f"InterpolateConvUpSampleLayer(factor={self.factor}, mode={self.mode}, temporal_upsample={self.temporal_upsample})"


class ChannelDuplicatingPixelShuffleUpSampleLayer(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        factor: int,
        temporal_upsample: bool = False,  # upsample on the temporal dimension as well
    ):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.factor = factor
        assert out_channels * factor**2 % in_channels == 0
        self.temporal_upsample = temporal_upsample

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() == 5:
            B, C, T, H, W = x.shape
            assert C == self.in_channels

        if self.temporal_upsample and T != 1:  # video input
            repeats = self.out_channels * self.factor**3 // self.in_channels
        else:
            repeats = self.out_channels * self.factor**2 // self.in_channels

        x = x.repeat_interleave(repeats, dim=1)

        if x.dim() == 4:  # original image-only training
            x = F.pixel_shuffle(x, self.factor)
        elif x.dim() == 5:  # [B, C, T, H, W]
            if self.temporal_upsample and T != 1:  # video input
                x = pixel_shuffle_3d(x, self.factor)
            else:
                x = x.permute(0, 2, 1, 3, 4)  # [B, T, C, H, W]
                x = F.pixel_shuffle(x, self.factor)  # on H and W only
                x = x.permute(0, 2, 1, 3, 4)  # [B, C, T, H, W]
        return x

    def __repr__(self):
        return f"ChannelDuplicatingPixelShuffleUpSampleLayer(in_channels={self.in_channels}, out_channels={self.out_channels}, factor={self.factor}, temporal_upsample={self.temporal_upsample})"


class LinearLayer(nn.Module):
    def __init__(
        self,
        in_features: int,
        out_features: int,
        use_bias=True,
        dropout=0,
        norm=None,
        act_func=None,
    ):
        super().__init__()

        self.dropout = nn.Dropout(dropout, inplace=False) if dropout > 0 else None
        self.linear = nn.Linear(in_features, out_features, use_bias)
        self.norm = build_norm(norm, num_features=out_features)
        self.act = build_act(act_func)

    def _try_squeeze(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() > 2:
            x = torch.flatten(x, start_dim=1)
        return x

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self._try_squeeze(x)
        if self.dropout:
            x = self.dropout(x)
        x = self.linear(x)
        if self.norm:
            x = self.norm(x)
        if self.act:
            x = self.act(x)
        return x


class IdentityLayer(nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x


#################################################################################
#                             Basic Blocks                                      #
#################################################################################


class DSConv(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size=3,
        stride=1,
        use_bias=False,
        norm=("bn2d", "bn2d"),
        act_func=("relu6", None),
    ):
        super().__init__()

        use_bias = val2tuple(use_bias, 2)
        norm = val2tuple(norm, 2)
        act_func = val2tuple(act_func, 2)

        self.depth_conv = ConvLayer(
            in_channels,
            in_channels,
            kernel_size,
            stride,
            groups=in_channels,
            norm=norm[0],
            act_func=act_func[0],
            use_bias=use_bias[0],
        )
        self.point_conv = ConvLayer(
            in_channels,
            out_channels,
            1,
            norm=norm[1],
            act_func=act_func[1],
            use_bias=use_bias[1],
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.depth_conv(x)
        x = self.point_conv(x)
        return x


class MBConv(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size=3,
        stride=1,
        mid_channels=None,
        expand_ratio=6,
        use_bias=False,
        norm=("bn2d", "bn2d", "bn2d"),
        act_func=("relu6", "relu6", None),
    ):
        super().__init__()

        use_bias = val2tuple(use_bias, 3)
        norm = val2tuple(norm, 3)
        act_func = val2tuple(act_func, 3)
        mid_channels = (
            round(in_channels * expand_ratio) if mid_channels is None else mid_channels
        )

        self.inverted_conv = ConvLayer(
            in_channels,
            mid_channels,
            1,
            stride=1,
            norm=norm[0],
            act_func=act_func[0],
            use_bias=use_bias[0],
        )
        self.depth_conv = ConvLayer(
            mid_channels,
            mid_channels,
            kernel_size,
            stride=stride,
            groups=mid_channels,
            norm=norm[1],
            act_func=act_func[1],
            use_bias=use_bias[1],
        )
        self.point_conv = ConvLayer(
            mid_channels,
            out_channels,
            1,
            norm=norm[2],
            act_func=act_func[2],
            use_bias=use_bias[2],
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.inverted_conv(x)
        x = self.depth_conv(x)
        x = self.point_conv(x)
        return x


class FusedMBConv(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size=3,
        stride=1,
        mid_channels=None,
        expand_ratio=6,
        groups=1,
        use_bias=False,
        norm=("bn2d", "bn2d"),
        act_func=("relu6", None),
    ):
        super().__init__()
        use_bias = val2tuple(use_bias, 2)
        norm = val2tuple(norm, 2)
        act_func = val2tuple(act_func, 2)

        mid_channels = (
            round(in_channels * expand_ratio) if mid_channels is None else mid_channels
        )

        self.spatial_conv = ConvLayer(
            in_channels,
            mid_channels,
            kernel_size,
            stride,
            groups=groups,
            use_bias=use_bias[0],
            norm=norm[0],
            act_func=act_func[0],
        )
        self.point_conv = ConvLayer(
            mid_channels,
            out_channels,
            1,
            use_bias=use_bias[1],
            norm=norm[1],
            act_func=act_func[1],
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.spatial_conv(x)
        x = self.point_conv(x)
        return x


class GLUMBConv(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size=3,
        stride=1,
        mid_channels=None,
        expand_ratio=6,
        use_bias=False,
        norm=(None, None, "ln2d"),
        act_func=("silu", "silu", None),
        is_video=False,
    ):
        super().__init__()
        use_bias = val2tuple(use_bias, 3)
        norm = val2tuple(norm, 3)
        act_func = val2tuple(act_func, 3)

        mid_channels = (
            round(in_channels * expand_ratio) if mid_channels is None else mid_channels
        )

        self.glu_act = build_act(act_func[1], inplace=False)
        self.inverted_conv = ConvLayer(
            in_channels,
            mid_channels * 2,
            1,
            use_bias=use_bias[0],
            norm=norm[0],
            act_func=act_func[0],
            is_video=is_video,
        )
        self.depth_conv = ConvLayer(
            mid_channels * 2,
            mid_channels * 2,
            kernel_size,
            stride=stride,
            groups=mid_channels * 2,
            use_bias=use_bias[1],
            norm=norm[1],
            act_func=None,
            is_video=is_video,
        )
        self.point_conv = ConvLayer(
            mid_channels,
            out_channels,
            1,
            use_bias=use_bias[2],
            norm=norm[2],
            act_func=act_func[2],
            is_video=is_video,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.inverted_conv(x)
        x = self.depth_conv(x)

        x, gate = torch.chunk(x, 2, dim=1)
        gate = self.glu_act(gate)
        x = x * gate

        x = self.point_conv(x)
        return x


class ResBlock(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size=3,
        stride=1,
        mid_channels=None,
        expand_ratio=1,
        use_bias=False,
        norm=("bn2d", "bn2d"),
        act_func=("relu6", None),
        is_video=False,
    ):
        super().__init__()
        use_bias = val2tuple(use_bias, 2)
        norm = val2tuple(norm, 2)
        act_func = val2tuple(act_func, 2)

        mid_channels = (
            round(in_channels * expand_ratio) if mid_channels is None else mid_channels
        )

        self.conv1 = ConvLayer(
            in_channels,
            mid_channels,
            kernel_size,
            stride,
            use_bias=use_bias[0],
            norm=norm[0],
            act_func=act_func[0],
            is_video=is_video,
        )
        self.conv2 = ConvLayer(
            mid_channels,
            out_channels,
            kernel_size,
            1,
            use_bias=use_bias[1],
            norm=norm[1],
            act_func=act_func[1],
            is_video=is_video,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv1(x)
        x = self.conv2(x)
        return x


class LiteMLA(nn.Module):
    r"""Lightweight multi-scale linear attention"""

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        heads: Optional[int] = None,
        heads_ratio: float = 1.0,
        dim=8,
        use_bias=False,
        norm=(None, "bn2d"),
        act_func=(None, None),
        kernel_func="relu",
        scales: tuple[int, ...] = (5,),
        eps=1.0e-15,
        is_video=False,
    ):
        super().__init__()
        self.eps = eps
        heads = int(in_channels // dim * heads_ratio) if heads is None else heads

        total_dim = heads * dim

        use_bias = val2tuple(use_bias, 2)
        norm = val2tuple(norm, 2)
        act_func = val2tuple(act_func, 2)

        self.dim = dim
        self.qkv = ConvLayer(
            in_channels,
            3 * total_dim,
            1,
            use_bias=use_bias[0],
            norm=norm[0],
            act_func=act_func[0],
            is_video=is_video,
        )
        conv_class = nn.Conv2d if not is_video else ChannelChunkConv3d
        self.aggreg = nn.ModuleList(
            [
                nn.Sequential(
                    conv_class(
                        3 * total_dim,
                        3 * total_dim,
                        scale,
                        padding=get_same_padding(scale),
                        groups=3 * total_dim,
                        bias=use_bias[0],
                    ),
                    conv_class(
                        3 * total_dim,
                        3 * total_dim,
                        1,
                        groups=3 * heads,
                        bias=use_bias[0],
                    ),
                )
                for scale in scales
            ]
        )
        self.kernel_func = build_act(kernel_func, inplace=False)

        self.proj = ConvLayer(
            total_dim * (1 + len(scales)),
            out_channels,
            1,
            use_bias=use_bias[1],
            norm=norm[1],
            act_func=act_func[1],
            is_video=is_video,
        )

    @torch.autocast(device_type="cuda", enabled=False)
    def relu_linear_att(self, qkv: torch.Tensor) -> torch.Tensor:
        if qkv.ndim == 5:
            B, _, T, H, W = list(qkv.size())
            is_video = True
        else:
            B, _, H, W = list(qkv.size())
            is_video = False

        if qkv.dtype == torch.float16:
            qkv = qkv.float()

        if qkv.ndim == 4:
            qkv = torch.reshape(
                qkv,
                (
                    B,
                    -1,
                    3 * self.dim,
                    H * W,
                ),
            )
        elif qkv.ndim == 5:
            qkv = torch.reshape(
                qkv,
                (
                    B,
                    -1,
                    3 * self.dim,
                    H * W * T,
                ),
            )
        q, k, v = (
            qkv[:, :, 0 : self.dim],
            qkv[:, :, self.dim : 2 * self.dim],
            qkv[:, :, 2 * self.dim :],
        )

        # lightweight linear attention
        q = self.kernel_func(q)
        k = self.kernel_func(k)

        # linear matmul
        trans_k = k.transpose(-1, -2)

        v = F.pad(v, (0, 0, 0, 1), mode="constant", value=1)
        vk = torch.matmul(v, trans_k)
        out = torch.matmul(vk, q)
        if out.dtype == torch.bfloat16:
            out = out.float()
        out = out[:, :, :-1] / (out[:, :, -1:] + self.eps)

        if not is_video:
            out = torch.reshape(out, (B, -1, H, W))
        else:
            out = torch.reshape(out, (B, -1, T, H, W))
        return out

    @torch.autocast(device_type="cuda", enabled=False)
    def relu_quadratic_att(self, qkv: torch.Tensor) -> torch.Tensor:
        B, _, H, W = list(qkv.size())

        qkv = torch.reshape(
            qkv,
            (
                B,
                -1,
                3 * self.dim,
                H * W,
            ),
        )
        q, k, v = (
            qkv[:, :, 0 : self.dim],
            qkv[:, :, self.dim : 2 * self.dim],
            qkv[:, :, 2 * self.dim :],
        )

        q = self.kernel_func(q)
        k = self.kernel_func(k)

        att_map = torch.matmul(k.transpose(-1, -2), q)  # b h n n
        original_dtype = att_map.dtype
        if original_dtype in [torch.float16, torch.bfloat16]:
            att_map = att_map.float()
        att_map = att_map / (
            torch.sum(att_map, dim=2, keepdim=True) + self.eps
        )  # b h n n
        att_map = att_map.to(original_dtype)
        out = torch.matmul(v, att_map)  # b h d n

        out = torch.reshape(out, (B, -1, H, W))
        return out

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # generate multi-scale q, k, v
        qkv = self.qkv(x)
        multi_scale_qkv = [qkv]
        for op in self.aggreg:
            multi_scale_qkv.append(op(qkv))
        qkv = torch.cat(multi_scale_qkv, dim=1)

        if qkv.ndim == 4:
            H, W = list(qkv.size())[-2:]
            # num_tokens = H * W
        elif qkv.ndim == 5:
            _, _, T, H, W = list(qkv.size())
            # num_tokens = H * W * T

        # if num_tokens > self.dim:
        out = self.relu_linear_att(qkv).to(qkv.dtype)
        # else:
        #     if self.is_video:
        #         raise NotImplementedError("Video is not supported for quadratic attention")
        #     out = self.relu_quadratic_att(qkv)
        out = self.proj(out)

        return out


class EfficientViTBlock(nn.Module):
    def __init__(
        self,
        in_channels: int,
        heads_ratio: float = 1.0,
        dim=32,
        expand_ratio: float = 4,
        scales: tuple[int, ...] = (5,),
        norm: str = "bn2d",
        act_func: str = "hswish",
        context_module: str = "LiteMLA",
        local_module: str = "MBConv",
        is_video: bool = False,
    ):
        super().__init__()
        if context_module == "LiteMLA":
            self.context_module = ResidualBlock(
                LiteMLA(
                    in_channels=in_channels,
                    out_channels=in_channels,
                    heads_ratio=heads_ratio,
                    dim=dim,
                    norm=(None, norm),
                    scales=scales,
                    is_video=is_video,
                ),
                IdentityLayer(),
            )
        else:
            raise ValueError(f"context_module {context_module} is not supported")
        if local_module == "MBConv":
            self.local_module = ResidualBlock(
                MBConv(
                    in_channels=in_channels,
                    out_channels=in_channels,
                    expand_ratio=expand_ratio,
                    use_bias=(True, True, False),
                    norm=(None, None, norm),
                    act_func=(act_func, act_func, None),
                    is_video=is_video,
                ),
                IdentityLayer(),
            )
        elif local_module == "GLUMBConv":
            self.local_module = ResidualBlock(
                GLUMBConv(
                    in_channels=in_channels,
                    out_channels=in_channels,
                    expand_ratio=expand_ratio,
                    use_bias=(True, True, False),
                    norm=(None, None, norm),
                    act_func=(act_func, act_func, None),
                    is_video=is_video,
                ),
                IdentityLayer(),
            )
        else:
            raise NotImplementedError(f"local_module {local_module} is not supported")

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.context_module(x)
        x = self.local_module(x)
        return x


#################################################################################
#                             Functional Blocks                                 #
#################################################################################


class ResidualBlock(nn.Module):
    def __init__(
        self,
        main: Optional[nn.Module],
        shortcut: Optional[nn.Module],
        post_act=None,
        pre_norm: Optional[nn.Module] = None,
    ):
        super().__init__()

        self.pre_norm = pre_norm
        self.main = main
        self.shortcut = shortcut
        self.post_act = build_act(post_act)

    def forward_main(self, x: torch.Tensor) -> torch.Tensor:
        if self.pre_norm is None:
            return self.main(x)
        else:
            return self.main(self.pre_norm(x))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.main is None:
            res = x
        elif self.shortcut is None:
            res = self.forward_main(x)
        else:
            res = self.forward_main(x) + self.shortcut(x)
            if self.post_act:
                res = self.post_act(res)
        return res


class DAGBlock(nn.Module):
    def __init__(
        self,
        inputs: dict[str, nn.Module],
        merge: str,
        post_input: Optional[nn.Module],
        middle: nn.Module,
        outputs: dict[str, nn.Module],
    ):
        super().__init__()

        self.input_keys = list(inputs.keys())
        self.input_ops = nn.ModuleList(list(inputs.values()))
        self.merge = merge
        self.post_input = post_input

        self.middle = middle

        self.output_keys = list(outputs.keys())
        self.output_ops = nn.ModuleList(list(outputs.values()))

    def forward(self, feature_dict: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
        feat = [
            op(feature_dict[key]) for key, op in zip(self.input_keys, self.input_ops)
        ]
        if self.merge == "add":
            feat = list_sum(feat)
        elif self.merge == "cat":
            feat = torch.concat(feat, dim=1)
        else:
            raise NotImplementedError
        if self.post_input is not None:
            feat = self.post_input(feat)
        feat = self.middle(feat)
        for key, op in zip(self.output_keys, self.output_ops):
            feature_dict[key] = op(feat)
        return feature_dict


class OpSequential(nn.Module):
    def __init__(self, op_list: list[Optional[nn.Module]]):
        super().__init__()
        valid_op_list = []
        for op in op_list:
            if op is not None:
                valid_op_list.append(op)
        self.op_list = nn.ModuleList(valid_op_list)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        for op in self.op_list:
            x = op(x)
        return x
