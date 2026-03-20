import re
import math

class RegexHelper:
    @staticmethod
    def suggest_regex(sample_text):
        """
        Suggest a regex pattern based on a sample string.
        Attempts to identify common formats like phone numbers, IDs, or repetitive patterns.
        """
        if not sample_text:
            return None, 0.0

        # 1. Check for common patterns
        # Phone: 09xx-xxx-xxx or similar
        if re.match(r'^09\d{2}-?\d{3}-?\d{3}$', sample_text):
            return r'09\d{2}-?\d{3}-?\d{3}', 0.95
        
        # Email
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', sample_text):
            return r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', 1.0

        # 2. General induction
        # If it's pure numbers
        if sample_text.isdigit():
            return f'\\d{{{len(sample_text)}}}', 0.5 + (0.05 * len(sample_text))
        
        # If it's numbers with delimiters
        if re.match(r'^[\d\s\-()]+$', sample_text):
            # Replace digits with \d, keep delimiters
            pattern = ""
            for char in sample_text:
                if char.isdigit():
                    if not pattern.endswith('\\d'):
                        pattern += '\\d'
                else:
                    pattern += re.escape(char)
            return pattern, 0.4
        
        # Default: Exact match (escaped)
        return re.escape(sample_text), 1.0

    @staticmethod
    def calculate_score(regex, samples, noise_text=""):
        """
        Calculate a confidence score for a regex based on how well it matches samples
        without matching 'noise' (false positives).
        """
        if not regex:
            return 0.0
        
        try:
            compiled_re = re.compile(regex)
        except re.error:
            return 0.0

        # Match rate among positive samples
        match_count = 0
        for sample in samples:
            if compiled_re.search(sample):
                match_count += 1
        
        pos_score = match_count / len(samples) if samples else 0
        
        # Penalty for noise (over-matching)
        noise_penalty = 0
        if noise_text:
            noise_matches = compiled_re.findall(noise_text)
            # Simple penalty based on frequency of noise matches
            noise_penalty = min(0.5, len(noise_matches) * 0.05)
            
        return max(0.0, pos_score - noise_penalty)

if __name__ == "__main__":
    # Quick test
    helper = RegexHelper()
    pattern, score = helper.suggest_regex("0912-345-678")
    print(f"Sample: 0912-345-678 -> Pattern: {pattern}, Score Sug: {score}")
    
    pattern, score = helper.suggest_regex("ABC-12345")
    print(f"Sample: ABC-12345 -> Pattern: {pattern}, Score Sug: {score}")
