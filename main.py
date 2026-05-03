from terraria_bot.crawlers.crawler import run_crawler
from terraria_bot.crawlers.structured_data_crawler import run_structured_data_crawler


MODE = "structured"
#MODE = "pages"

if __name__ == "__main__":
    if MODE == "pages":
        run_crawler()

    elif MODE == "structured":
        run_structured_data_crawler()

    else:
        raise ValueError(f"Nieznany MODE: {MODE}")