
from src.name_utils import guess_first_last_from_author_query, names_match

def test_name_inversion():
    real_given = "Stenford"
    real_family = "Ruvinga"
    
    # query 1: "Stenford Ruvinga"
    q1 = "Stenford Ruvinga"
    f1, l1 = guess_first_last_from_author_query(q1)
    match1 = names_match(f1, l1, real_given, real_family)
    print(f"Query '{q1}' -> Parsed: Given='{f1}', Family='{l1}' -> Match: {match1}")
    
    # query 2: "Ruvinga Stenford"
    q2 = "Ruvinga Stenford"
    f2, l2 = guess_first_last_from_author_query(q2)
    match2 = names_match(f2, l2, real_given, real_family)
    print(f"Query '{q2}' -> Parsed: Given='{f2}', Family='{l2}' -> Match: {match2}")

if __name__ == "__main__":
    test_name_inversion()
