"""
Singleton model manager for lazy-loading and caching ML models.

Prevents multiple model loads and provides a central access point
for all pipeline models.
"""

from typing import Any


class ModelManager:
    """
    Singleton manager for lazy-loading and caching ML models.

    All models are loaded on first access and cached for reuse.
    Use ModelManager.clear() to release all cached models.
    """

    _instance = None
    _models: dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._models = {}
        return cls._instance

    def get_ner_pipeline(self):
        """
        Load and cache the clinical NER pipeline.

        Returns:
            transformers.Pipeline for token classification
        """
        if "ner" not in self._models:
            from transformers import pipeline
            from cliniq.config import MODEL_REGISTRY

            self._models["ner"] = pipeline(
                "token-classification",
                model=MODEL_REGISTRY["CLINICAL_NER"],
                aggregation_strategy="simple",
                device=-1,  # CPU
            )
        return self._models["ner"]

    def get_embedder(self):
        """
        Load and cache the sentence embedder.

        Returns:
            sentence_transformers.SentenceTransformer
        """
        if "embedder" not in self._models:
            from sentence_transformers import SentenceTransformer
            from cliniq.config import MODEL_REGISTRY

            self._models["embedder"] = SentenceTransformer(
                MODEL_REGISTRY["EMBEDDER"]
            )
        return self._models["embedder"]

    def get_cross_encoder(self):
        """
        Load and cache the cross-encoder reranker.

        Returns:
            sentence_transformers.CrossEncoder
        """
        if "cross_encoder" not in self._models:
            from sentence_transformers import CrossEncoder
            from cliniq.config import MODEL_REGISTRY

            self._models["cross_encoder"] = CrossEncoder(
                MODEL_REGISTRY["RERANKER"]
            )
        return self._models["cross_encoder"]

    def get_reasoning_llm(self):
        """
        Load and cache the reasoning LLM.

        Returns:
            tuple[AutoModelForCausalLM, AutoTokenizer]
        """
        if "reasoning_llm" not in self._models:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            from cliniq.config import MODEL_REGISTRY

            model_id = MODEL_REGISTRY["REASONING_LLM"]
            tokenizer = AutoTokenizer.from_pretrained(model_id)
            model = AutoModelForCausalLM.from_pretrained(model_id)
            self._models["reasoning_llm"] = (model, tokenizer)
        return self._models["reasoning_llm"]

    def get_multimodal(self):
        """
        Load and cache the multimodal vision-language model.

        Returns:
            tuple[AutoModel, AutoProcessor]
        """
        if "multimodal" not in self._models:
            from transformers import AutoModel, AutoProcessor
            from cliniq.config import MODEL_REGISTRY

            model_id = MODEL_REGISTRY["MULTIMODAL"]
            processor = AutoProcessor.from_pretrained(model_id)
            model = AutoModel.from_pretrained(model_id)
            self._models["multimodal"] = (model, processor)
        return self._models["multimodal"]

    @classmethod
    def clear(cls):
        """Release all cached models to free memory."""
        if cls._instance is not None:
            cls._instance._models.clear()
