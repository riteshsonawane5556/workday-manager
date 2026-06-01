import os
from dotenv import load_dotenv
from nylas import Client

load_dotenv()

NYLAS_API_KEY = os.environ["NYLAS_API_KEY"]
NYLAS_GRANT_ID = os.environ["NYLAS_GRANT_ID"]

nylas = Client(api_key=NYLAS_API_KEY)
