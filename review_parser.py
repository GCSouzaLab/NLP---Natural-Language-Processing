from bs4 import BeautifulSoup
import re

REVIEW_CARD_WRAPPER_CLASS = "mSOQy emJoM"
REVIEW_CARD_CLASS = "_c"
RATING_CLASSES = ["MyMKp u Q1", "evwcZ"]
TEXT_CLASSES = ["JguWG", "yCeTE"]
TITLE_CLASSES = ["biGQs _P SewaP qWPrE ncFvv ezezH", "yCeTE"]
LOCATION_NUM_CONTRIBUTIONS_CLASSES = ["biGQs _P navcl"]
DATE_CLASSES = ["BNelO"]


def get_reviews(document: BeautifulSoup) -> list[dict]:

    reviews = []

    # Busca todos os cards de review dentro do documento HTML
    review_cards = __get_review_cards(document)

    # Se não encontrar cards, retorna lista vazia
    if not review_cards:
        return reviews

    # Percorre cada card individualmente
    for review_card in review_cards:
        try:
            rating_text = __safe_get_text_in_class_hierarchy(review_card, RATING_CLASSES)
            rating = rating_text.split()[0] if rating_text else ""

            text = __safe_get_text_in_class_hierarchy(review_card, TEXT_CLASSES)
            title = __safe_get_text_in_class_hierarchy(review_card, TITLE_CLASSES)
            location = __get_review_location(review_card)
            num_contributions = __get_review_num_contributions(review_card)
            date = __get_review_date(review_card)

            reviews.append({
                "rating": rating,
                "title": title,
                "text": text,
                "location": location,
                "num_contributions": num_contributions,
                "date": date
            })

        except Exception as e:
            print(f"Erro ao processar review: {e}")
            continue

    return reviews


def __get_review_cards(document: BeautifulSoup) -> list[BeautifulSoup]:
    review_card_wrapper = document.find(class_=REVIEW_CARD_WRAPPER_CLASS)

    if not review_card_wrapper:
        return []

    review_cards = review_card_wrapper.find_all(class_=REVIEW_CARD_CLASS)
    return review_cards


def __safe_get_text_in_class_hierarchy(root: BeautifulSoup, classes: list[str]) -> str:
    element = __get_element_in_class_hierarchy(root, classes)

    if not element:
        return ""

    return __clear_text(element.get_text(" ", strip=True))


def __get_element_in_class_hierarchy(root: BeautifulSoup, classes: list[str]):
    element = root

    for class_ in classes:
        if element is None:
            return None
        element = element.find(class_=class_)

    return element


def __get_review_location(review_card: BeautifulSoup) -> str:
    element = __get_element_in_class_hierarchy(review_card, LOCATION_NUM_CONTRIBUTIONS_CLASSES)

    if not element:
        return ""

    spans = element.find_all("span")

    if len(spans) == 2:
        return __clear_text(spans[0].get_text(" ", strip=True))

    return ""


def __get_review_num_contributions(review_card: BeautifulSoup) -> str:
    element = __get_element_in_class_hierarchy(review_card, LOCATION_NUM_CONTRIBUTIONS_CLASSES)

    if not element:
        return ""

    spans = element.find_all("span")

    if not spans:
        return ""

    texto = __clear_text(spans[-1].get_text(" ", strip=True))

    # Extrai apenas o número do texto "12 contribuições" -> "12"
    match = re.search(r"\d+", texto)
    if match:
        return match.group(0)

    return texto


def __get_review_date(review_card: BeautifulSoup) -> str:
    element = __get_element_in_class_hierarchy(review_card, DATE_CLASSES)

    if not element:
        return ""

    div = element.find("div")

    if not div:
        return __clear_text(element.get_text(" ", strip=True))

    texto = __clear_text(div.get_text(" ", strip=True))

    # Remove o prefixo inicial quando existir algo como "Avaliado em "
    if len(texto) > 9:
        return texto[9:].strip()

    return texto


def __clear_text(text: str) -> str:
    return text.replace("undefined", "").strip()


def print_reviews(reviews: list[dict]):
    if len(reviews) > 0:
        print("-" * 40)

    for review in reviews:
        print(f"Rating: {review['rating']}")
        print(f"Title: {review['title']}")
        print("\nText:")
        print(review['text'], "\n")
        print(f"Location: {review['location']}")
        print(f"Number of Contributions: {review['num_contributions']}")
        print(f"Date: {review['date']}")
        print("-" * 40)
