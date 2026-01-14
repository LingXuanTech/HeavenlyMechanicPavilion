import asyncio
import json
import os
import re
from datetime import datetime
from typing import Annotated

ticker_to_company = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "GOOGL": "Google",
    "AMZN": "Amazon",
    "TSLA": "Tesla",
    "NVDA": "Nvidia",
    "TSM": "Taiwan Semiconductor Manufacturing Company OR TSMC",
    "JPM": "JPMorgan Chase OR JP Morgan",
    "JNJ": "Johnson & Johnson OR JNJ",
    "V": "Visa",
    "WMT": "Walmart",
    "META": "Meta OR Facebook",
    "AMD": "AMD",
    "INTC": "Intel",
    "QCOM": "Qualcomm",
    "BABA": "Alibaba",
    "ADBE": "Adobe",
    "NFLX": "Netflix",
    "CRM": "Salesforce",
    "PYPL": "PayPal",
    "PLTR": "Palantir",
    "MU": "Micron",
    "SQ": "Block OR Square",
    "ZM": "Zoom",
    "CSCO": "Cisco",
    "SHOP": "Shopify",
    "ORCL": "Oracle",
    "X": "Twitter OR X",
    "SPOT": "Spotify",
    "AVGO": "Broadcom",
    "ASML": "ASML ",
    "TWLO": "Twilio",
    "SNAP": "Snap Inc.",
    "TEAM": "Atlassian",
    "SQSP": "Squarespace",
    "UBER": "Uber",
    "ROKU": "Roku",
    "PINS": "Pinterest",
}


async def fetch_top_from_category_async(
    category: Annotated[str, "Category to fetch top post from. Collection of subreddits."],
    date: Annotated[str, "Date to fetch top posts from."],
    max_limit: Annotated[int, "Maximum number of posts to fetch."],
    query: Annotated[str, "Optional query to search for in the subreddit."] = None,
    data_path: Annotated[
        str,
        "Path to the data folder. Default is 'reddit_data'.",
    ] = "reddit_data",
):
    """Async version of fetch_top_from_category."""
    base_path = data_path

    all_content = []

    if not os.path.exists(os.path.join(base_path, category)):
        return []

    category_dirs = os.listdir(os.path.join(base_path, category))
    if not category_dirs:
        return []

    if max_limit < len(category_dirs):
        # Instead of raising error, just adjust limit
        limit_per_subreddit = 1
    else:
        limit_per_subreddit = max_limit // len(category_dirs)

    for data_file in category_dirs:
        if not data_file.endswith(".jsonl"):
            continue

        all_content_curr_subreddit = []

        # Use run_in_executor for file I/O to keep it async-friendly
        loop = asyncio.get_event_loop()

        def read_file():
            results = []
            with open(os.path.join(base_path, category, data_file), "rb") as f:
                for line in f:
                    if not line.strip():
                        continue
                    parsed_line = json.loads(line)
                    post_date = datetime.utcfromtimestamp(parsed_line["created_utc"]).strftime(
                        "%Y-%m-%d"
                    )
                    if post_date != date:
                        continue

                    if "company" in category and query:
                        search_terms = []
                        if "OR" in ticker_to_company.get(query, query):
                            search_terms = ticker_to_company.get(query, query).split(" OR ")
                        else:
                            search_terms = [ticker_to_company.get(query, query)]
                        search_terms.append(query)

                        found = False
                        for term in search_terms:
                            if re.search(term, parsed_line["title"], re.IGNORECASE) or re.search(
                                term, parsed_line["selftext"], re.IGNORECASE
                            ):
                                found = True
                                break
                        if not found:
                            continue

                    results.append(
                        {
                            "title": parsed_line["title"],
                            "content": parsed_line["selftext"],
                            "url": parsed_line["url"],
                            "upvotes": parsed_line["ups"],
                            "posted_date": post_date,
                        }
                    )
            return results

        all_content_curr_subreddit = await loop.run_in_executor(None, read_file)
        all_content_curr_subreddit.sort(key=lambda x: x["upvotes"], reverse=True)
        all_content.extend(all_content_curr_subreddit[:limit_per_subreddit])

    return all_content


def fetch_top_from_category(
    category: Annotated[str, "Category to fetch top post from. Collection of subreddits."],
    date: Annotated[str, "Date to fetch top posts from."],
    max_limit: Annotated[int, "Maximum number of posts to fetch."],
    query: Annotated[str, "Optional query to search for in the subreddit."] = None,
    data_path: Annotated[
        str,
        "Path to the data folder. Default is 'reddit_data'.",
    ] = "reddit_data",
):
    base_path = data_path

    all_content = []

    if max_limit < len(os.listdir(os.path.join(base_path, category))):
        raise ValueError(
            "REDDIT FETCHING ERROR: max limit is less than the number of files in the category. Will not be able to fetch any posts"
        )

    limit_per_subreddit = max_limit // len(os.listdir(os.path.join(base_path, category)))

    for data_file in os.listdir(os.path.join(base_path, category)):
        # check if data_file is a .jsonl file
        if not data_file.endswith(".jsonl"):
            continue

        all_content_curr_subreddit = []

        with open(os.path.join(base_path, category, data_file), "rb") as f:
            for i, line in enumerate(f):
                # skip empty lines
                if not line.strip():
                    continue

                parsed_line = json.loads(line)

                # select only lines that are from the date
                post_date = datetime.utcfromtimestamp(parsed_line["created_utc"]).strftime(
                    "%Y-%m-%d"
                )
                if post_date != date:
                    continue

                # if is company_news, check that the title or the content has the company's name (query) mentioned
                if "company" in category and query:
                    search_terms = []
                    if "OR" in ticker_to_company[query]:
                        search_terms = ticker_to_company[query].split(" OR ")
                    else:
                        search_terms = [ticker_to_company[query]]

                    search_terms.append(query)

                    found = False
                    for term in search_terms:
                        if re.search(term, parsed_line["title"], re.IGNORECASE) or re.search(
                            term, parsed_line["selftext"], re.IGNORECASE
                        ):
                            found = True
                            break

                    if not found:
                        continue

                post = {
                    "title": parsed_line["title"],
                    "content": parsed_line["selftext"],
                    "url": parsed_line["url"],
                    "upvotes": parsed_line["ups"],
                    "posted_date": post_date,
                }

                all_content_curr_subreddit.append(post)

        # sort all_content_curr_subreddit by upvote_ratio in descending order
        all_content_curr_subreddit.sort(key=lambda x: x["upvotes"], reverse=True)

        all_content.extend(all_content_curr_subreddit[:limit_per_subreddit])

    return all_content
