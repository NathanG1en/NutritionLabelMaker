from sentence_transformers import SentenceTransformer
model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
embedding = model.encode("Test sentence", convert_to_tensor=True)
print(embedding.shape)
