import ast
import asyncio
import os
import re
from asyncio import Semaphore

import pandas as pd
from dotenv import load_dotenv
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage
from more_itertools import chunked
from tqdm.asyncio import tqdm_asyncio

from configs.templates import review_categorization_template
from configs.topic_list import VALID_TYPES, topic_list

load_dotenv()

semaphore = Semaphore(3)  # Limit concurrent Bedrock requests to keep throughput stable.


def get_bedrock_credentials():
    """Read AWS Bedrock credentials from the environment, raising a clear error if missing."""
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_REGION", "us-east-2")

    if not access_key or not secret_key:
        raise ValueError(
            "Missing AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY. "
            "Copy .env.example to .env and fill in your AWS Bedrock credentials to use the AI Tagger."
        )

    return access_key, secret_key, region


def build_bedrock_llm(model_id, temperature, max_tokens):
    access_key, secret_key, region = get_bedrock_credentials()
    return ChatBedrock(
        model_id=model_id,
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        model_kwargs={
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
    )


def normalize_bedrock_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif hasattr(block, "text"):
                parts.append(block.text)
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content)


def invoke_bedrock(prompt, model_id, temperature, max_tokens):
    llm = build_bedrock_llm(model_id, temperature, max_tokens)
    response = llm.invoke([HumanMessage(content=prompt)])
    return normalize_bedrock_content(response.content)


async def get_response_bedrock(prompt, model="global.anthropic.claude-sonnet-4-5-20250929-v1:0", temperature=0.2, max_tokens=2000, retry_count=0):
    """Send a request to Claude via AWS Bedrock asynchronously, with retries."""
    async with semaphore:
        try:
            return await asyncio.to_thread(
                invoke_bedrock,
                prompt,
                model,
                temperature,
                max_tokens,
            )
        except Exception as e:
            if retry_count < 5:
                wait_time = 3 * (retry_count + 1)
                print(f"⚠️ Bedrock request failed — retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
                return await get_response_bedrock(prompt, model, temperature, max_tokens, retry_count + 1)

            print(f"🚨 Bedrock request failed: {e}")
            return ['Unknown', 'Unknown', 'Unknown']


async def categorize_review(idx, review_text, args, company_name):
    """Send one review to Claude and parse the result."""
    if not review_text.strip():
        return idx, ["Unknown", "Unknown", "Unknown"]

    prompt = review_categorization_template.format(
        company_name=company_name, reviews=review_text, topic_list=topic_list
    )

    try:
        result = await get_response_bedrock(prompt, args.gpt_model, args.temperature, args.max_tokens)
        result = result.strip()

        # Remove prefixes like "Output:", "Result:", etc.
        result = re.sub(r'^[\w\s:]*', '', result).strip()

        parsed = ast.literal_eval(result)
        if len(parsed) == 3 and parsed[0] in VALID_TYPES:
            if parsed[1:] == ['Irrelevant', 'Irrelevant']:
                parsed[0] = 'Irrelevant'
            elif parsed[2] == 'General Feedback':
                parsed[1] = 'General'
            return idx, parsed
    except Exception as e:
        print(f"[Error] Review {idx}: {e}")

    return idx, ["Unknown", "Unknown", "Unknown"]


async def categorize_reviews_async(input_path, output_path, args, key_names, company_name, batch_size=100):
    """Batch process reviews asynchronously, saving progress after every batch."""
    df = pd.read_csv(input_path)
    print(f"🧾 Loaded {len(df)} reviews with columns: {df.columns.tolist()}")

    for key in key_names:
        if key not in df.columns:
            raise KeyError(f"Missing column: {key}")

    df[['Type', 'Lvl1 Category', 'Lvl2 Category']] = None

    for chunk in tqdm_asyncio(chunked(list(df.iterrows()), batch_size), desc="Categorizing batches"):
        tasks = []
        for idx, row in chunk:
            review_text = " ".join(str(row[k]) for k in key_names if pd.notna(row[k])).strip()
            tasks.append(categorize_review(idx, review_text, args, company_name))

        results = await asyncio.gather(*tasks)

        for idx, cats in results:
            df.loc[idx, ["Type", "Lvl1 Category", "Lvl2 Category"]] = cats

        df.to_csv(output_path, index=False)

    print(f"✅ Categorization complete. Saved to: {output_path}")


async def retry_unknowns(output_path, args, key_names, company_name, max_retries=10):
    """Retry categorization for rows still marked 'Unknown', up to max_retries passes."""
    for attempt in range(1, max_retries + 1):
        df = pd.read_csv(output_path)

        unknown_mask = df['Type'].isna() | df['Type'].eq("Unknown")
        df_unknown = df.loc[unknown_mask].copy()

        if df_unknown.empty:
            print("🎉 All reviews categorized successfully!")
            return

        print(f"🔁 Retry attempt {attempt}/{max_retries}: {len(df_unknown)} unknown reviews found.")

        tasks = []
        for idx, row in df_unknown.iterrows():
            review_text = " ".join(str(row[k]) for k in key_names if pd.notna(row[k])).strip()

            prompt = review_categorization_template.format(
                company_name=company_name, reviews=review_text, topic_list=topic_list
            )

            task = asyncio.create_task(
                get_response_bedrock(
                    prompt=prompt,
                    model=args.gpt_model,
                    temperature=args.temperature,
                    max_tokens=args.max_tokens
                )
            )
            tasks.append((idx, task))

        for idx, task in tasks:
            result = await task
            try:
                parsed = ast.literal_eval(result)
                if len(parsed) == 3:
                    df.at[idx, "Type"] = parsed[0]
                    df.at[idx, "Lvl1 Category"] = parsed[1]
                    df.at[idx, "Lvl2 Category"] = parsed[2]
            except Exception:
                pass  # keep as Unknown if parsing fails

        df.to_csv(output_path, index=False)
        print(f"✅ Retry {attempt} completed. File updated in place: {output_path}")

    print("❌ Max retries reached. Some reviews may still be Unknown.")


class Args:
    def __init__(self, gpt_model="global.anthropic.claude-sonnet-4-5-20250929-v1:0", temperature=0.2, max_tokens=2000):
        self.gpt_model = gpt_model
        self.temperature = temperature
        self.max_tokens = max_tokens


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input_path", required=True)
    parser.add_argument("--output_path", required=True)
    parser.add_argument("--key_names", nargs="+", default=["Content"])
    parser.add_argument("--company", required=True)
    parser.add_argument("--batch_size", type=int, default=100)
    args_cli = parser.parse_args()

    args = Args()

    asyncio.run(categorize_reviews_async(
        input_path=args_cli.input_path,
        output_path=args_cli.output_path,
        args=args,
        key_names=args_cli.key_names,
        company_name=args_cli.company,
        batch_size=args_cli.batch_size
    ))

    asyncio.run(retry_unknowns(
        output_path=args_cli.output_path,
        args=args,
        key_names=args_cli.key_names,
        company_name=args_cli.company
    ))
