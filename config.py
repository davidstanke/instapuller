import os
import sqlalchemy

from os import path
from sqlalchemy import create_engine
from shutil import copyfile

db_type = os.environ.get("DB_TYPE") or "mysql"

if (db_type=="sqlite3"): # for testing; use a local sqlite3 file as DB
    
    db_file="instapuller.db"

    if (not path.exists(db_file)): # copy from the template to a new db
        copyfile("misc/instapuller-template.db",db_file)
            
    db = create_engine("sqlite:///"+db_file, echo=True)
else: 
    db_user = os.environ.get("DB_USER")
    db_pass = os.environ.get("DB_PASS")
    db_name = os.environ.get("DB_NAME")
    cloud_sql_connection_name = os.environ.get("CLOUD_SQL_CONNECTION_NAME")

    db = sqlalchemy.create_engine(
        sqlalchemy.engine.url.URL(
            drivername="mysql+pymysql",
            username=db_user,
            password=db_pass,
            database=db_name,
            query={
                "unix_socket": "/cloudsql/{}".format(cloud_sql_connection_name)},
        ),
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,  # 30 seconds
        pool_recycle=1800,  # 30 minutes
    )

