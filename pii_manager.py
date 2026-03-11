import json
import yaml
import os
import re
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
import time

class PIIManager:
    def __init__(self, config_path='config.yaml', vault_path='vault.json'):
        self.config_path = f"{os.getcwd()}/{config_path}"
        self.vault_path = f"{os.getcwd()}/{vault_path}"
        self.load_config()
        
        # Configure Presidio for Chinese support
        configuration = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "zh", "model_name": "zh_core_web_sm"}],
        }
        
        provider = NlpEngineProvider(nlp_configuration=configuration)
        nlp_engine = provider.create_engine()
        
        self.analyzer = AnalyzerEngine(
            nlp_engine=nlp_engine,
            default_score_threshold=self.score_threshold
        )
        
        self.setup_custom_recognizers()
        
        self.anonymizer = AnonymizerEngine()
        self.vault = {}
        self.load_vault()

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self.entities = config.get('entities', ['PERSON', 'PHONE_NUMBER', 'EMAIL_ADDRESS'])
                self.custom_patterns = config.get('custom_patterns', [])
                self.score_threshold = config.get('score_threshold', 0.4)
        else:
            self.entities = ['PERSON', 'PHONE_NUMBER', 'EMAIL_ADDRESS']
            self.custom_patterns = []
            self.score_threshold = 0.4

    def setup_custom_recognizers(self):
        # We can add custom patterns here
        for pattern_def in self.custom_patterns:
            pattern = Pattern(name=pattern_def['name'], regex=pattern_def['regex'], score=pattern_def['score'])
            recognizer = PatternRecognizer(
                supported_entity=pattern_def['name'], 
                patterns=[pattern],
                supported_language=pattern_def.get('language', 'zh')
            )
            self.analyzer.registry.add_recognizer(recognizer)
            if pattern_def['name'] not in self.entities:
                self.entities.append(pattern_def['name'])

        # Explicitly add Email recognizer for Chinese if it's not working by default
        # Presidio's predefined EmailRecognizer usually supports only 'en'/'es'/'fr' etc.
        # We add a generic one for 'zh'
        email_pattern = Pattern(
            name="EMAIL_ADDRESS_ZH",
            regex=r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            score=1.0
        )
        email_recognizer = PatternRecognizer(
            supported_entity="EMAIL_ADDRESS",
            patterns=[email_pattern],
            supported_language='zh'
        )
        self.analyzer.registry.add_recognizer(email_recognizer)

    def load_vault(self):
        if os.path.exists(self.vault_path):
            with open(self.vault_path, 'r', encoding='utf-8') as f:
                try:
                    self.vault = json.load(f)
                except:
                    self.vault = {}
        else:
            self.vault = {}

    def save_vault(self):
        with open(self.vault_path, 'w', encoding='utf-8') as f:
            json.dump(self.vault, f, ensure_ascii=False, indent=2)

    def is_pii_potential(self, text):
        # FAST PATH: Quick regex check for common PII patterns
        # If none of these match, there's a high probability no PII exists.
        
        # Patterns: 
        # 1. Email: @
        # 2. Numbers: 8+ digits (Phone/ID/CC)
        # 3. Chinese surnames followed by 1-2 chars
        # 4. Address markers (市, 區, 縣, 路)
        # 5. Crypto addresses (starts with 0x or similar, handled by basic check)
        
        # Surname regex
        surnames = "王李張劉陳楊黃趙周吳徐孫馬朱胡郭林何羅高"
        if re.search(f'[{surnames}][\u4e00-\u9fa5]{{1,2}}', text): return True
        if '@' in text: return True
        if re.search(r'\d{8,}', text): return True
        if re.search(r'[市縣區鄉鎮路街巷弄號]', text): return True
        if re.search(r'0x[a-fA-F0-9]{40}', text): return True
        
        return False

    def anonymize_text(self, text):
        # Character limit for performance
        if len(text) > 10000:
            # print("Text too long for real-time PII scan, skipping.")
            return text, False

        # Check if text already contains our tags to avoid re-processing upon restoration
        if re.search(r'<[A-Z_]+_\d+>', text):
            return text, False

        # Removed fast path check to ensure all text is scanned properly, as it was overly restrictive
        # Fast path check removed for better accuracy.

        start_time = time.time()
        
        results = self.analyzer.analyze(text=text, entities=self.entities, language='zh')
        
        if not results:
            return text, False
            
        # Sort results by start index
        sorted_results = sorted(results, key=lambda x: x.start)
        
        entity_counts = {}
        new_text = ""
        last_idx = 0
        current_mappings = {}
        
        for res in sorted_results:
            # Skip if we already covered this part due to overlaps
            if res.start < last_idx:
                continue
                
            entity_type = res.entity_type
            entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
            tag = f"<{entity_type}_{entity_counts[entity_type]}>"
            
            original_val = text[res.start:res.end]
            current_mappings[tag] = original_val
            
            new_text += text[last_idx:res.start] + tag
            last_idx = res.end
            
        new_text += text[last_idx:]
        
        # Store in vault
        self.vault.update(current_mappings)
        self.save_vault()
        
        end_time = time.time()
        # duration = end_time - start_time
        # if duration > 0.5:
        #     print(f"PII Analysis took {duration:.2f}s")
        
        return new_text, True

    def restore_text(self, text):
        # Find all tags like <ANYTHING_1>
        import re
        tags = re.findall(r'<[A-Z_]+_\d+>', text)
        restored_text = text
        changed = False
        
        # We need to be careful replacing tags to avoid partial matches
        # but since we have _\d+ it's unique.
        
        # Sort tags by index length or just use regex replacement
        # Let's do it simply for now.
        for tag in set(tags):
            if tag in self.vault:
                restored_text = restored_text.replace(tag, self.vault[tag])
                changed = True
        
        return restored_text, changed
