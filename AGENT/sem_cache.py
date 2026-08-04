

from redisvl.extensions.cache.llm import SemanticCache
from redisvl.utils.vectorize import HFTextVectorizer


llmcache = SemanticCache(
    name="llmcache",                                          
    redis_url="redis://127.0.0.1:6379",                       
    distance_threshold=0.1,                                   
    vectorizer=HFTextVectorizer("redis/langcache-embed-v1"), 
)