from torch.utils.data import Dataset
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from PIL import Image
import os


from scraping.data import connection_url, download_file_from_s3
from scraping.tables import Text
from scraping.settings import SETTINGS


class CustomTextDataset(Dataset):
    def __init__(self):
        self.engine = create_engine(connection_url(asyncronous=False))
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.length: int = self.session.query(Text).order_by(Text.id.desc()).first().id

    def __len__(self):
        return self.length

    def __getitem__(self, idx):
        ma = self.session.query(Text).where(Text.id == (idx + 1))
        text = ma.first()
        image_path = text.image_path
        text = text.text

        download_file_from_s3(
            bucket_name=SETTINGS.S3_BUCKET, object_key=image_path, file=image_path
        )
        image = Image.open(image_path)
        os.remove(image_path)
        return text, image
