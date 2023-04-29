from __future__ import annotations

import dataclasses
import os
from typing import Any, List, Optional

import numpy as np
import orjson

from autogpt.llm_utils import create_embedding_with_ada
from autogpt.memory.base import MemoryProviderSingleton

EMBED_DIM = 1536
SAVE_OPTIONS = orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_SERIALIZE_DATACLASS


def create_default_embeddings():
    return np.zeros((0, EMBED_DIM)).astype(np.float32)


@dataclasses.dataclass
class CacheContent:
    texts: List[str] = dataclasses.field(default_factory=list)
    embeddings: np.ndarray = dataclasses.field(
        default_factory=create_default_embeddings
    )


class LocalCache():
    # on load, load our database
    def __init__(self, organization_name, agent_id) -> None:

        self.filename = f"permanent_storage/organizations/{organization_name}/agents/{agent_id}_memory.json"
        if os.path.exists(self.filename):
            with open(self.filename, "rb") as f:
                loaded = orjson.loads(f.read())
                loaded["embeddings"] = np.array(loaded["embeddings"], dtype=np.float32)  # Convert loaded embeddings to a NumPy array
                self.data = CacheContent(**loaded)

        else:
            print(
                f"Warning: The file '{self.filename}' does not exist. "
                "Local memory would not be saved to a file."
            )
            self.data = CacheContent()

    def add(self, text: str):
        """
        Add text to our list of texts, add embedding as row to our
            embeddings-matrix

        Args:
            text: str

        Returns: None
        """
        if "Command Error:" in text:
            return ""
        self.data.texts.append(text)

        embedding = create_embedding_with_ada(text)

        vector = np.array(embedding).astype(np.float32)
        vector = vector[np.newaxis, :]
        self.data.embeddings = np.concatenate(
            [
                self.data.embeddings,
                vector,
            ],
            axis=0,
        )

        with open(self.filename, "wb") as f:
            out = orjson.dumps(self.data, option=SAVE_OPTIONS)
            f.write(out)
        return text

    def clear(self) -> str:
        """
        Clears the redis server.

        Returns: A message indicating that the memory has been cleared.
        """
        self.data = CacheContent()
        return "Obliviated"

    def get(self, data: str) -> list[Any] | None:
        """
        Gets the data from the memory that is most relevant to the given data.

        Args:
            data: The data to compare to.

        Returns: The most relevant data.
        """
        return self.get_relevant(data, 1)


    def get_relevant(self, text: str, k: int) -> list[Any]:
        """ "
        matrix-vector mult to find score-for-each-row-of-matrix
         get indices for top-k winning scores
         return texts for those indices
        Args:
            text: str
            k: int

        Returns: List[str]
        """
        embedding = create_embedding_with_ada(text)

        scores = np.dot(self.data.embeddings, embedding)

        top_k_indices = np.argsort(scores)[-k:][::-1]

        return [self.data.texts[i] for i in top_k_indices]

    def get_stats(self) -> tuple[int, tuple[int, ...]]:
        """
        Returns: The stats of the local cache.
        """
        return len(self.data.texts), self.data.embeddings.shape
