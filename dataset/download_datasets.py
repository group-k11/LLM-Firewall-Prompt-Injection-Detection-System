"""
Download datasets from HuggingFace for the LLM Firewall project.
Downloads:
  1. deepset/prompt-injections (malicious prompts)
  2. tatsu-lab/alpaca (safe prompts)
"""

from datasets import load_dataset
import pandas as pd
import os

DATASET_DIR = os.path.dirname(os.path.abspath(__file__))


def download_prompt_injections():
    """Download the deepset/prompt-injections dataset."""
    print("[*] Downloading deepset/prompt-injections dataset...")
    dataset = load_dataset("deepset/prompt-injections", trust_remote_code=True)

    df = pd.DataFrame(dataset["train"])
    output_path = os.path.join(DATASET_DIR, "prompt_injection_dataset.csv")
    df.to_csv(output_path, index=False)
    print(f"[+] Saved {len(df)} rows to {output_path}")
    return df


def download_alpaca():
    """Download the tatsu-lab/alpaca dataset (safe prompts)."""
    print("[*] Downloading tatsu-lab/alpaca dataset...")
    dataset = load_dataset("tatsu-lab/alpaca", trust_remote_code=True)

    df = pd.DataFrame(dataset["train"])
    output_path = os.path.join(DATASET_DIR, "safe_prompts.csv")
    df.to_csv(output_path, index=False)
    print(f"[+] Saved {len(df)} rows to {output_path}")
    return df


if __name__ == "__main__":
    download_prompt_injections()
    download_alpaca()
    print("\n[DONE] All datasets downloaded successfully!")
