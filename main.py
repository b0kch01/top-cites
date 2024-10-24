from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass
import requests
import requests_cache
import urllib
from termcolor import colored
from time import sleep

requests_cache.install_cache('request_cache')


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
            print(
                f"    {colored(str(self.citations) + ' citations', 'yellow')}")


def parse_article_from_div(div: Tag):
    title = div.select_one("h3>*:last-child").text
    author = div.select_one(".gs_a").text.replace("\\xa0", " ")

    cites_tags = list(
        filter(lambda r: "Cited by" in r.text, div.select("a")))

    if len(cites_tags) > 0:
        cites_tag = cites_tags[0]
        cited_by = cites_tag.attrs["href"]
        cites = int(cites_tag.text.split(" ")[-1])

        return Article(title, author, cites, cited_by)

    else:
        return Article(title, author, -1, None)


def grab_articles_from_page(page, sort_by_citations=False):
    articles = []

    results = page.select(".gs_r.gs_or.gs_scl")

    for result in results:
        article = parse_article_from_div(result)

        if article is not None:
            articles.append(article)

    if sort_by_citations:
        return sorted(articles, key=lambda x: x.citations, reverse=True)
    else:
        return articles


def search_articles(query):
    url_encoded_query = urllib.parse.quote(query)
    url = f"https://scholar.google.com/scholar?as_vis=1&q=${url_encoded_query}&hl=en"

    res = requests.get(url)
    if res.status_code != 200:
        raise Exception(f"Failed to fetch results for query {query}")

    results_page = BeautifulSoup(str(res.content), features="lxml")
    results = grab_articles_from_page(results_page)

    return results


def grab_citations(link, page=0):
    url = "https://scholar.google.com" + link + "&start=" + str(page * 10)

    res = requests.get(url)
    if res.status_code != 200:
        raise Exception(f"Failed to fetch citations for {link}")

    citations_page = BeautifulSoup(str(res.content), features="lxml")
    results = grab_articles_from_page(citations_page, sort_by_citations=False)

    return results


def print_menu():
    print("""
 ▗▄▄▖▗▄▄▄▖▗▄▄▄▖▗▄▄▄▖
▐▌     █    █  ▐▌   
▐▌     █    █  ▐▛▀▀▘
▝▚▄▄▖▗▄█▄▖  █  ▐▙▄▄▖
        """)

    red_clear = colored('\"clear\"', 'red')
    print(f"{red_clear} to clear request cache. Watch out for rate limits!\n")


def main():
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

    results = search_articles(query)

    print()

    for i, article in enumerate(results):
        article.display(i)

    print()

    choice = int(input(
        colored("Choose an article to view its citations> ", "blue")))

    chosen_article = results[choice]

    print(f"[Selected] \"{chosen_article.title}\"")
    print()
    print(f"-- Author: {chosen_article.author}")
    print(f"-- Cited by: {chosen_article.cited_by}")
    print(f"-- Citations: {chosen_article.citations}")

    all_citations = []

    # We will have this limit for now
    for page in range(50):
        citations = grab_citations(chosen_article.cited_by, page=page)
        all_citations += citations
        all_citations.sort(key=lambda x: x.citations, reverse=False)

        print()
        print(f"Viewing {page+1} page(s) of citations (sorted):")
        for i, citation in enumerate(all_citations):
            citation.display(i)

        if page >= chosen_article.citations // 10:
            print("\nNo more pages to view.")
            break

        cont = input(
            colored("Press enter to get next page or 'q' to quit> ", "blue"))
        if cont == "q":
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(colored("\nKeyboard interrupt detected. Exiting...", "red"))
