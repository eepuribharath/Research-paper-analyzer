"""Persistent FAISS cosine-similarity index with a SQLite-backed ID mapping."""
from pathlib import Path
import json
import numpy as np
import faiss
from config import INDEX_DIR, EMBEDDING_DIM

class VectorStore:
    def __init__(self, directory: Path = INDEX_DIR):
        self.directory=Path(directory); self.directory.mkdir(parents=True,exist_ok=True)
        self.index_path=self.directory/"chunks.faiss"; self.map_path=self.directory/"mapping.json"
        self.index=None; self.ids=[]; self.load()

    def load(self):
        if self.index_path.exists() and self.map_path.exists():
            self.index=faiss.read_index(str(self.index_path)); self.ids=json.loads(self.map_path.read_text(encoding="utf-8"))
            if self.index.d != EMBEDDING_DIM or self.index.ntotal != len(self.ids): raise ValueError("FAISS index and mapping are inconsistent; rebuild the index.")
        else: self.index=faiss.IndexFlatIP(EMBEDDING_DIM); self.ids=[]

    def save(self):
        faiss.write_index(self.index,str(self.index_path)); self.map_path.write_text(json.dumps(self.ids),encoding="utf-8")

    def add(self, chunk_ids, vectors):
        vectors=np.asarray(vectors,dtype="float32")
        if vectors.ndim!=2 or vectors.shape[1]!=EMBEDDING_DIM: raise ValueError(f"Expected embedding dimension {EMBEDDING_DIM}.")
        keep=[(cid,v) for cid,v in zip(chunk_ids,vectors) if cid not in self.ids]
        if keep:
            self.index.add(np.stack([v for _,v in keep]).astype("float32")); self.ids.extend(cid for cid,_ in keep); self.save()

    def search(self, vector, top_k=5):
        if not self.ids: return []
        q=np.asarray(vector,dtype="float32").reshape(1,-1)
        if q.shape[1]!=self.index.d: raise ValueError("Query embedding dimension does not match the index.")
        scores,indices=self.index.search(q,min(int(top_k),len(self.ids)))
        return [{"chunk_id":self.ids[int(i)],"score":float(s)} for s,i in zip(scores[0],indices[0]) if i>=0]

    def remove(self, chunk_ids):
        removed=set(chunk_ids)
        if removed:
            pairs=[cid for cid in self.ids if cid not in removed]
            # Flat indexes cannot delete IDs reliably; compact by rebuilding from retained vectors.
            old=self.index.reconstruct_n(0,self.index.ntotal) if self.index.ntotal else np.empty((0,self.index.d),dtype="float32")
            vectors=[v for cid,v in zip(self.ids,old) if cid not in removed]
            self.index=faiss.IndexFlatIP(EMBEDDING_DIM)
            if vectors: self.index.add(np.stack(vectors).astype("float32"))
            self.ids=pairs; self.save()

    def rebuild(self, chunk_ids, vectors):
        self.index=faiss.IndexFlatIP(EMBEDDING_DIM); self.ids=[]
        if len(chunk_ids): self.add(chunk_ids,vectors)
        else: self.save()
