from regex_helper import RegexHelper

def test_regex_helper():
    helper = RegexHelper()
    
    test_cases = [
        ("0912-345-678", "09\\d{2}-?\\d{3}-?\\d{3}"),
        ("alston@example.com", "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"),
        ("12345678", "\\d{8}"),
        ("ID-99-88-77", "ID\\-99\\-88\\-77") # Default exact match for mixed formats not yet handled
    ]
    
    print("--- Testing Regex Suggestion ---")
    for sample, expected_prefix in test_cases:
        pattern, score = helper.suggest_regex(sample)
        print(f"Input: {sample}")
        print(f"Suggested: {pattern} (Score: {score})")
        if pattern.startswith(expected_prefix) or pattern == expected_prefix:
            print("  ✅ Match")
        else:
            print("  ❌ Mismatch")
            
    print("\n--- Testing Score Calculation ---")
    # Positive match
    score = helper.calculate_score(r"\d{3}", ["123", "456", "789"])
    print(f"Score for \\d{{3}} on numbers: {score} (Expected 1.0)")
    
    # Partial match
    score = helper.calculate_score(r"\d{3}", ["123", "abc", "789"])
    print(f"Score for \\d{{3}} on mixed: {score} (Expected 0.66...)")
    
    # Noise penalty
    noise = "This is a test with 123 and 456."
    score = helper.calculate_score(r"\d{3}", ["123", "456"], noise_text=noise)
    print(f"Score for \\d{{3}} with noise '123, 456': {score} (Expected < 1.0)")

if __name__ == "__main__":
    test_regex_helper()
