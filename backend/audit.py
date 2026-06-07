import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
try:
    from app.models.models import Base
    print("Models:")
    for mapper in Base.registry.mappers:
        print(f" - {mapper.class_.__name__} -> {mapper.local_table.name}")
except Exception as e:
    print(f"Error loading models: {e}")

try:
    from app.main import app
    print("\nRoutes:")
    for route in app.routes:
        print(f" - {getattr(route, 'methods', ['GET'])} {getattr(route, 'path', '')}")
except Exception as e:
    print(f"Error loading routes: {e}")
