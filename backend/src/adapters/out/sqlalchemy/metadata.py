from adapters.out.sqlalchemy.base import Base
from adapters.out.sqlalchemy.shared.outbox import models as outbox_models
from sqlalchemy import MetaData

_ = outbox_models

target_metadata: MetaData = Base.metadata
