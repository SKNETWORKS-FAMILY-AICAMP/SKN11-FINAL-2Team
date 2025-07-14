from src.database.qdrant_client import get_qdrant_client;
  print(get_qdrant_client().get_collection_info()['points_count'])
