def build_rag_prompt(question: str, context_chunks: list[str]) -> str:
    context = "\n\n".join(context_chunks)

    prompt = f"""
You are a helpful assistant.
Answer the question ONLY using the context below.
If the answer is not contained in the context, say "Not found in the document."

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
"""
    return prompt.strip()
