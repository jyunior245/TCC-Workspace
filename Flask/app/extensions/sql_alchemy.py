import json
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy(engine_options={
    "json_serializer": lambda obj: json.dumps(obj, ensure_ascii=False)
})
