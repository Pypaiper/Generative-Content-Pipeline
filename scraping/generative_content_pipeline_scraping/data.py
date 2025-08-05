import json
import logging
import boto3
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from botocore.exceptions import ClientError
import requests
import zipfile
from io import BytesIO


from .settings import SETTINGS

logger = logging.getLogger(__name__)


def aws_kms_secret(secret_name: str, region_name: str) -> str:
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)
    return str(client.get_secret_value(SecretId=secret_name)["SecretString"])


def connection_url(asyncronous=True) -> URL:
    if SETTINGS.DB_HOST == "":
        return URL.create("sqlite+aiosqlite" if asyncronous else "sqlite")

    msg_source = ""
    if SETTINGS.DB_PASSWORD is not None:
        msg_source = "environment"
        username = SETTINGS.DB_USER
        password = SETTINGS.DB_PASSWORD.get_secret_value()
    else:
        msg_source = "AWS Secrets Manager"
        secret = json.loads(
            aws_kms_secret(
                SETTINGS.DB_PASSWORD_AWS_KMS_URI, SETTINGS.DB_PASSWORD_AWS_KMS_REGION
            )
        )

        username = secret["username"]
        password = secret["password"]

    url = URL.create(
        "postgresql+asyncpg" if asyncronous else "postgresql",
        username=username,
        password=password,
        host=SETTINGS.DB_HOST,
        port=int(SETTINGS.DB_PORT),
        database=SETTINGS.DB_NAME,
    )

    logger.info(
        f"Using DB credentials supplied by: {msg_source}. "
        f"Connection string: {url.render_as_string(hide_password=True)}."
    )

    return url


def save_file_to_s3(bucket_name, object_key, key):
    """
    Saves content to an S3 object in LocalStack.
    """
    try:
        # Create the bucket if it doesn't exist
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            logger.info(f"Bucket '{bucket_name}' already exists.")
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                logger.info(f"Bucket '{bucket_name}' does not exist. Creating...")
                s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={
                        "LocationConstraint": SETTINGS.S3_REGION,
                    },
                )
                logger.info(f"Bucket '{bucket_name}' created successfully.")
            else:
                raise

        # Upload the content
        s3_client.upload_file(object_key, bucket_name, key)
        logger.info(f"Successfully saved '{object_key}' to bucket '{bucket_name}'.")

    except ClientError as e:
        logger.error(f"Error saving to S3: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")


def download_file_from_s3(bucket_name, object_key, file):
    """
    Downloads content from an S3 object in LocalStack to local file.
    """
    try:
        # Create the bucket if it doesn't exist
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            logger.info(f"Bucket '{bucket_name}' already exists.")
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                logger.info(f"Bucket '{bucket_name}' does not exist. Creating...")
                s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={
                        "LocationConstraint": SETTINGS.S3_REGION,
                    },
                )
                logger.info(f"Bucket '{bucket_name}' created successfully.")
            else:
                raise

        # Upload the content
        s3_client.download_file(bucket_name, object_key, file)
        logger.info(f"Successfully downloaded '{object_key}' to file '{file}'.")

    except ClientError as e:
        logger.error(f"Error downloading to S3: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")


def get_css(classes, selectors):
    """
    Extracts all css style from a webpage
    """
    all_css = dict()
    for _class in classes:
        for selector, sel_css in selectors.items():
            if selector.startswith("table") and "." + _class in selector:
                all_css.update(sel_css)
    return all_css


def download_and_extract_zip(url, extract_path="."):
    """
    Downloads a ZIP file from a given URL and extracts its contents.

    Args:
        url (str): The URL of the ZIP file to download.
        extract_path (str): The directory where the contents will be extracted.
                            Defaults to the current directory.
    """
    try:
        # Send a GET request to the URL to download the file content
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Use BytesIO to treat the downloaded content as a file-like object
        zip_file_in_memory = BytesIO(response.content)

        # Open the ZIP file from memory
        with zipfile.ZipFile(zip_file_in_memory, "r") as zf:
            # Extract all contents to the specified path
            zf.extractall(extract_path)
        logger.info(f"ZIP file downloaded from {url} and extracted to {extract_path}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading the file: {e}")
    except zipfile.BadZipFile:
        logger.error("Error: The downloaded file is not a valid ZIP file.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")


engine = create_async_engine(connection_url(asyncronous=True), echo=False)

async_session = async_sessionmaker(engine, expire_on_commit=False)
s3_client = None
try:
    # Try to connect to s3 as though we are in aws environment
    # (credentials aren't present or necessary here)
    s3_client = boto3.client("s3")
except ImportError:
    # Not in aws use local credentials
    # This environment may be a docker notebook with LocalStack provided s3
    s3_client = boto3.client(
        "s3",
        endpoint_url=SETTINGS.S3_HOST,
        aws_access_key_id=SETTINGS.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=SETTINGS.AWS_SECRET_ACCESS_KEY,
    )
