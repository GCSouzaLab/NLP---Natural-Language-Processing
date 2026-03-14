from bs4 import BeautifulSoup

REVIEW_CARD_WRAPPER_CLASS = "mSOQy emJoM"
REVIEW_CARD_CLASS = "_c"

USER_CLASSES = ["QIHsu Zb", "biGQs _P ezezH"]
RATING_CLASSES = ["MyMKp u Q1", "evwcZ"]
TEXT_CLASSES = ["JguWG", "yCeTE"]
TITLE_CLASSES = ["biGQs _P SewaP qWPrE ncFvv ezezH", "yCeTE"]
LOCATION_NUM_CONTRIBUTIONS_CLASSES = ["biGQs _P navcl"]
DATE_CLASSES = ["BNelO"]



def get_reviews(document: BeautifulSoup) -> list[dict]:

    reviews = []

    review_cards = __get_review_cards(document)

    for review_card in review_cards:

        user = __get_text_in_class_hierarchy(review_card, USER_CLASSES)
        rating = __get_text_in_class_hierarchy(review_card, RATING_CLASSES).split()[0]
        text = __get_text_in_class_hierarchy(review_card, TEXT_CLASSES)
        title = __get_text_in_class_hierarchy(review_card, TITLE_CLASSES)

        location = __get_review_location(review_card)
        num_contributions = __get_review_num_contributions(review_card)

        date = __get_element_in_class_hierarchy(review_card, DATE_CLASSES).div.text[9:]
        
        reviews.append({
            "user": user,
            "rating": rating,
            "title": title,
            "text": text,
            "location": location,
            "num_contributions": num_contributions,
            "date": date
        })

    return reviews

def __get_review_cards(document: BeautifulSoup) -> list[BeautifulSoup]:
    review_card_wrapper = document.find(class_=REVIEW_CARD_WRAPPER_CLASS)
    review_cards = review_card_wrapper.find_all(class_=REVIEW_CARD_CLASS)

    return review_cards
        

def __get_text_in_class_hierarchy(root: BeautifulSoup, classes: list[str]) -> str:
    element = __get_element_in_class_hierarchy(root, classes)
    return __clear_text(element.text)


def __get_element_in_class_hierarchy(root: BeautifulSoup, classes: list[str]) -> BeautifulSoup:
    element = root
    for class_ in classes:
        element = element.find(class_=class_)

    return element


def __get_review_location(review_card: BeautifulSoup) -> str:
    element = __get_element_in_class_hierarchy(review_card, LOCATION_NUM_CONTRIBUTIONS_CLASSES)
    spans = element.find_all("span")

    if len(spans) == 2:
        return __clear_text(spans[0].text)
    
    return ""


def __get_review_num_contributions(review_card: BeautifulSoup) -> str:
    element = __get_element_in_class_hierarchy(review_card, LOCATION_NUM_CONTRIBUTIONS_CLASSES)
    spans = element.find_all("span")

    return __clear_text(spans[-1].text)[0:1]


def __clear_text(text: str) -> str:
    return text.replace("undefined", "").strip()


def print_reviews(reviews: list[dict]):

    if len(reviews) > 0:
        print("-" * 40)

    for review in reviews:
        print(f"User: {review['user']}")
        print(f"Rating: {review['rating']}")
        print(f"Title: {review['title']}")
        print("\nText:")
        print(review['text'], "\n")
        print(f"Location: {review['location']}")
        print(f"Number of Contributions: {review['num_contributions']}")
        print(f"Date: {review['date']}")
        print("-" * 40)