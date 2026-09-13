from adapters.out.sqlalchemy.base import Base
from adapters.out.sqlalchemy.capture import models as capture_models
from adapters.out.sqlalchemy.distill import models as distill_models
from adapters.out.sqlalchemy.shared.outbox import models as outbox_models
from sqlalchemy import MetaData

_ = outbox_models
_ = capture_models
_ = distill_models

target_metadata: MetaData = Base.metadata
