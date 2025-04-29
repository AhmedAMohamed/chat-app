from transformers import AutoTokenizer, AutoModelForCausalLM

# Use a pipeline as a high-level helper
from transformers import pipeline

pipe = pipeline("text-generation", model="meta-llama/Meta-Llama-3-8B")

model_name = "meta-llama/Llama-3-8B"  # Replace with the actual model name if known

try:
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)

    input_text = "Write a short story about a cat who can talk."
    input_ids = tokenizer.encode(input_text, return_tensors="pt")

    # Generate the output
    output = model.generate(input_ids, max_length=200, num_return_sequences=1)

    # Decode the output
    generated_text = tokenizer.decode(output[0], skip_special_tokens=True)
    print(generated_text)

except Exception as e:
    print(f"Error loading model {model_name}: {e}")
    print("Please ensure the model name is correct and accessible on Hugging Face Hub or locally.")