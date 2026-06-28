import chromadb
from chromadb.utils import embedding_functions

print("🚀 Starting download of ChromaDB embedding model (~80MB)...")
print("Grab a coffee and let this reach 100%!")

# This forcefully triggers the background download without any web timeouts
ef = embedding_functions.DefaultEmbeddingFunction()
ef(["This is a test to force the download."])

print("✅ Download 100% complete! It is now cached forever.")