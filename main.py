from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass
import requests
import requests_cache
import urllib
from termcolor import colored
from time import sleep
import csv

from cookies import get_cookies


@dataclass
class Article:
    title: str
    author: str
    citations: int
    cited_by: str

    def display(self, i):
        print(f" {i}. {self.title}")
        print(f"    {colored(self.author, 'green')}")
        if self.citations == -1:
            print(f"    {colored('No citations reported', 'red')}")
        else:
            print(f"    {colored(str(self.citations) + ' citations', 'yellow')}")


class RequestsManager:
    def __init__(self):
        self.session = requests.session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        }

        self.solve_captcha()

    def solve_captcha(self):
        self.cookie = {"GSP": get_cookies()}

    def get(self, url):
        res = self.session.get(url, cookies=self.cookie, headers=self.headers)
        if "not a robot" in str(res.content):
            self.solve_captcha()

        return self.session.get(url, cookies=self.cookie, headers=self.headers)


def parse_article_from_div(div: Tag):
    title = div.select_one("h3>*:last-child").text
    author = div.select_one(".gs_a").text.replace("\\xa0", " ")

    cites_tags = list(filter(lambda r: "Cited by" in r.text, div.select("a")))

    if len(cites_tags) > 0:
        cites_tag = cites_tags[0]
        cited_by = cites_tag.attrs["href"]
        cites = int(cites_tag.text.split(" ")[-1])

        return Article(title, author, cites, cited_by)

    else:
        return Article(title, author, -1, None)


def grab_articles_from_page(page):
    articles = []

    results = page.select(".gs_r.gs_or.gs_scl")

    for result in results:
        article = parse_article_from_div(result)

        if article is not None:
            articles.append(article)

    if len(articles) == 0:
        print("no results! (did you get detected?)")
        return []

    return articles


def search_articles(rm: RequestsManager, query):
    url_encoded_query = urllib.parse.quote(query)
    url = f"https://scholar.google.com/scholar?as_vis=1&q=${url_encoded_query}&hl=en"

    res = rm.get(url)
    if res.status_code != 200:
        raise Exception(f"Failed to fetch results for query {query}")

    results_page = BeautifulSoup(str(res.content), features="lxml")
    results = grab_articles_from_page(results_page)

    return results


def grab_citations(rm, link, page=0):
    if link.startswith("https://scholar.google.com/scholar?cites"):
        if "&start=" in link:
            url = link.replace("&start=", "")
        url = link
    else:
        url = "https://scholar.google.com" + link + "&start=" + str(page * 10)

    res = rm.get(url)
    if res.status_code != 200:
        raise Exception(f"Failed to fetch citations for {link}")

    citations_page = BeautifulSoup(str(res.content), features="lxml")
    results = grab_articles_from_page(citations_page)

    return results


def export(citations):
    citations.sort(key=lambda x: x.citations, reverse=True)
    count = int(input("How many to export? (0 for all) > "))
    count = len(citations) if count == 0 else count

    print("Exporting citations...", end="")

    with open("top-citations.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow(["Title", "Author", "Cited by", "Citations"])
        for citation in citations[:count]:
            writer.writerow(
                [citation.title, citation.author, citation.cited_by, citation.citations]
            )

    print(colored("Done!", "green"))


def print_menu():
    print("""
 ▗▄▄▖▗▄▄▄▖▗▄▄▄▖▗▄▄▄▖
▐▌     █    █  ▐▌
▐▌     █    █  ▐▛▀▀▘
▝▚▄▄▖▗▄█▄▖  █  ▐▙▄▄▖
        """)

    red_clear = colored('"clear"', "red")
    print(f"{red_clear} to clear request cache. Watch out for rate limits!\n")


def main():
    rm = RequestsManager()

    print_menu()

    while True:
        query = input(colored("Google Scholar Search> ", "blue"))
        if query == "clear":
            requests_cache.clear()
            print(colored("Request cache cleared!", "green"))
        elif query == "exit":
            exit(0)
        elif len(query) > 0:
            break

    if query.startswith("https://scholar.google.com/scholar?cites"):
        chosen_article = Article("Custom", "Custom", -1, query)
    else:
        results = search_articles(rm, query)

        print()

        for i, article in enumerate(results):
            article.display(i)

        print()

        choice = int(
            input(colored("Choose an article to view its citations> ", "blue"))
        )

        chosen_article = results[choice]

        print(f'[Selected] "{chosen_article.title}"')
        print()
        print(f"-- Author: {chosen_article.author}")
        print(f"-- Cited by: {chosen_article.cited_by}")
        print(f"-- Citations: {chosen_article.citations}")

    all_citations = []

    # We will have this limit for now
    for page in range(50):
        citations = grab_citations(rm, chosen_article.cited_by, page=page)
        all_citations += citations
        all_citations.sort(key=lambda x: x.citations, reverse=True)

        print()
        print(f"Viewing {page+1} page(s) of citations (sorted):")
        for i, citation in enumerate(all_citations):
            citation.display(i)

        if page >= chosen_article.citations // 10:
            print("\nNo more pages to view.")

            if input("Export results? [y/n]") == "y":
                export(all_citations)

            break

        cont = input(
            colored("[Enter] For next page; [q] to quit; [e] to export> ", "blue")
        )
        if cont == "e":
            export(all_citations)
            break
        if cont == "q":
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(colored("\nKeyboard interrupt detected. Exiting...", "red"))
