import json
import re
import unicodedata
from pathlib import Path
import os
import threading
from rapidfuzz import process, fuzz

from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_core.prompts import ChatPromptTemplate

WIKI_DB_DIR = Path("chroma_wiki_db")
STRUCTURED_DB_DIR = Path("chroma_structured_db")
ITEM_NAMES_FILE = Path("item_names.json")

class TerrariaEngine:
    def __init__(self):
        # States: NOT_STARTED, LOADING_MODELS, MODELS_LOADED, LOADING_DBS, DBS_LOADED, BUILDING_INDEX, READY, ERROR
        self.state = "NOT_STARTED"
        self.error_message = ""
        self.progress_percent = 0
        self.progress_msg = "Awaiting initialization..."
        
        # Engine instances
        self.embeddings = None
        self.llm = None
        self.wiki_db = None
        self.structured_db = None
        self.item_names = []
        self.normalized_item_names = {}
        self.normalized_item_name_keys = []
        self.item_aliases = {}
        self.item_alias_keys = []
        
        # Wiki lookup
        self.wiki_title_lookup = {}
        self.wiki_title_keys = []
        
        # Prompts and chains
        self.chain = None
        self.structured_chain = None

        # Lock for thread safety during background indexing
        self.lock = threading.Lock()

    def set_status(self, state, msg="", progress=0, error=""):
        self.state = state
        self.progress_msg = msg
        self.progress_percent = progress
        self.error_message = error

    def get_status(self):
        return {
            "state": self.state,
            "progress_msg": self.progress_msg,
            "progress_percent": self.progress_percent,
            "error_message": self.error_message,
            "stats": {
                "items_loaded": len(self.item_names),
                "wiki_titles_indexed": len(self.wiki_title_keys),
                "wiki_db_count": self.wiki_db._collection.count() if self.wiki_db else 0,
                "structured_db_count": self.structured_db._collection.count() if self.structured_db else 0
            } if self.state in ["DBS_LOADED", "BUILDING_INDEX", "READY"] else {}
        }

    def init_models(self):
        try:
            import ollama
            self.set_status("LOADING_MODELS", "Connecting to Ollama and checking available models...", 10)
            
            # Query active models in Ollama
            try:
                models_info = ollama.list()
                models_list = models_info.get("models", [])
                available_model_names = [m.get("model") for m in models_list]
            except Exception as ex:
                print("Error listing Ollama models:", ex)
                available_model_names = []
            
            # 1. Check and pull Embeddings
            has_embed = any("nomic-embed-text" in m for m in available_model_names)
            if not has_embed:
                self.set_status("LOADING_MODELS", "Pulling nomic-embed-text embeddings (~274 MB)...", 25)
                ollama.pull("nomic-embed-text")
                
            self.set_status("LOADING_MODELS", "Initializing Ollama nomic-embed-text embeddings...", 45)
            self.embeddings = OllamaEmbeddings(model="nomic-embed-text")
            
            # 2. Select and pull target LLM (qwen2.5:14b)
            llm_model = "qwen2.5:14b"
            has_qwen = any("qwen2.5:14b" in m for m in available_model_names)
            
            if not has_qwen:
                self.set_status("LOADING_MODELS", "Pulling qwen2.5:14b (~9 GB)... This might take some time depending on your download speed.", 60)
                ollama.pull("qwen2.5:14b")
                
            self.set_status("LOADING_MODELS", "Initializing Ollama qwen2.5:14b LLM...", 85)
            self.llm = OllamaLLM(model="qwen2.5:14b", temperature=0)
            
            # Initialize prompt templates and chains
            system_prompt = """
You are a Terraria QA assistant.

Answer in the same language as the user's question.

Answer ONLY using the provided CONTEXT.
Do not use outside knowledge.
Do not guess.
Do not infer.
Do not add facts that are not explicitly present in CONTEXT.
Do not invent items, recipes, stats, numbers, NPCs, bosses, drops, strategies, or mechanics.

Do not list drops, loot, detailed statistics, version-specific notes, or long item lists unless the user explicitly asks about drops, loot, stats, or item lists.

If the user asks for a general description, give a short general description based only on CONTEXT.

If the answer is not directly stated in the CONTEXT, reply exactly:
"I cannot answer this based on the provided text."

Use a short answer.
For every factual claim, it must be directly supported by CONTEXT.

CONTEXT:
{context}
"""
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{question}")
            ])
            self.chain = prompt | self.llm

            structured_prompt = ChatPromptTemplate.from_messages([
                ("system", """
You are a Terraria assistant.

Answer in the same language as the user's question.

Use ONLY the FACTS below.
Do not use outside knowledge.
Do not invent, omit, or change item names, ingredients, stats, numbers, crafting stations, or effects.
Do not add commentary, opinions, platform/version information, edition information, or extra explanations unless they are explicitly present in FACTS.

Never change numbers from FACTS.
If the FACTS contain "Total ingredients", use those exact totals.
If an ingredient amount is listed as 8x, keep it as 8x.
Do not assume missing ingredients or deeper crafting trees.

For item stats, answer only with the stats present in FACTS.
For recipes, answer only with ingredients and crafting station.
Do not explain where an item comes from unless FACTS explicitly say it.

Do not mention legacy unless the user asks about legacy.
If there are alternative recipes, mention them as alternatives.

Give a natural but concise answer.
Avoid marketing-like phrases such as "unique", "impressive", "powerful", or "special" unless those exact words are in FACTS.

FACTS:
{context}
"""),
                ("human", "{question}")
            ])
            self.structured_chain = structured_prompt | self.llm

            self.set_status("MODELS_LOADED", "Models loaded successfully!", 100)
            return True
        except Exception as e:
            self.set_status("ERROR", f"Failed to load models: {str(e)}", 0, str(e))
            return False

    def init_databases(self):
        if self.state != "MODELS_LOADED":
            self.set_status("ERROR", "Please load models first.", 0, "Models not loaded.")
            return False
        
        try:
            self.set_status("LOADING_DBS", "Opening chroma_wiki_db...", 20)
            self.wiki_db = Chroma(
                persist_directory=str(WIKI_DB_DIR),
                embedding_function=self.embeddings
            )
            
            self.set_status("LOADING_DBS", "Opening chroma_structured_db...", 50)
            self.structured_db = Chroma(
                persist_directory=str(STRUCTURED_DB_DIR),
                embedding_function=self.embeddings
            )
            
            self.set_status("LOADING_DBS", "Loading item_names.json...", 80)
            if not ITEM_NAMES_FILE.exists():
                raise FileNotFoundError(f"Missing {ITEM_NAMES_FILE.name}")
                
            with ITEM_NAMES_FILE.open("r", encoding="utf-8") as file:
                self.item_names = json.load(file)
            
            # Populate normalized items and aliases
            self.normalized_item_names = {
                self.normalize_for_matching(name): name
                for name in self.item_names
                if self.normalize_for_matching(name)
            }
            self.normalized_item_name_keys = list(self.normalized_item_names.keys())
            
            self.item_aliases = {}
            for normalized_name, original_name in self.normalized_item_names.items():
                self.item_aliases[normalized_name] = original_name
                self.item_aliases[normalized_name.replace(" ", "")] = original_name
            self.item_alias_keys = list(self.item_aliases.keys())
            
            self.set_status("DBS_LOADED", "Vector databases and item lists loaded successfully!", 100)
            return True
        except Exception as e:
            self.set_status("ERROR", f"Failed to load databases: {str(e)}", 0, str(e))
            return False

    def build_wiki_index(self):
        if self.state != "DBS_LOADED":
            self.set_status("ERROR", "Please load databases first.", 0, "Databases not loaded.")
            return
            
        def run_indexing():
            with self.lock:
                try:
                    self.set_status("BUILDING_INDEX", "Preparing index construction...", 0)
                    total = self.wiki_db._collection.count()
                    batch_size = 5000
                    wiki_title_lookup = {}
                    
                    for offset in range(0, total, batch_size):
                        if self.state == "ERROR":
                            return
                        percent = int((offset / total) * 100)
                        self.set_status("BUILDING_INDEX", f"Indexing wiki page titles: {offset} of {total} chunks...", percent)
                        
                        wiki_meta_data = self.wiki_db._collection.get(
                            include=["metadatas"],
                            limit=batch_size,
                            offset=offset
                        )
                        
                        for metadata in wiki_meta_data["metadatas"]:
                            for key in ["title", "page"]:
                                title = metadata.get(key, "")
                                if not title:
                                    continue
                                
                                normalized_title = self.normalize_for_matching(title)
                                if len(normalized_title) < 4:
                                    continue
                                    
                                if normalized_title not in wiki_title_lookup:
                                    wiki_title_lookup[normalized_title] = title

                    self.wiki_title_lookup = wiki_title_lookup
                    self.wiki_title_keys = list(wiki_title_lookup.keys())
                    self.set_status("READY", f"Engine is ready! Loaded {len(self.wiki_title_keys)} wiki pages and {len(self.item_names)} items.", 100)
                except Exception as e:
                    self.set_status("ERROR", f"Error building wiki index: {str(e)}", 0, str(e))
        
        threading.Thread(target=run_indexing, daemon=True).start()
        return True

    # TEXT PROCESSING UTILITIES
    @staticmethod
    def normalize_text(text: str):
        text = text.lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(char for char in text if not unicodedata.combining(char))
        return text

    @classmethod
    def normalize_for_matching(cls, text: str):
        text = cls.normalize_text(text)
        text = re.sub(r"[^a-z0-9]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    STOPWORDS = {
        "how", "to", "the", "a", "an", "is", "are", "what", "which", "with",
        "craft", "crafted", "crafting", "recipe", "use", "used", "for",
        "stats", "stat", "damage", "defense", "effect", "works",
        "jaki", "jakie", "jaka", "jak", "sie", "się", "ma", "maja", "mają",
        "co", "to", "czym", "jest", "dziala", "dzialaja", "dzialanie",
        "statystyki", "statystyk", "crafting", "receptura", "skladniki",
        "skladnikow", "uzyc", "uzywa", "uzycie", "dzialaja", "dzialają"
    }

    def strip_question_words(self, question: str):
        normalized = self.normalize_for_matching(question)
        words = [
            word for word in normalized.split()
            if word not in self.STOPWORDS and len(word) > 1
        ]
        return " ".join(words)

    QUESTION_TYPES = {
        "recipe": [
            "craft", "crafted", "crafting", "recipe",
            "ingredient", "ingredients", "material", "materials",
            "receptur", "skladnik", "skladniki",
            "wytworz", "stworz", "zrob", "robic",
            "jak zrobic", "jak stworzyc", "jak scraftowac",
            "ile potrzebuje", "ile potrzeba", "how many materials"
        ],
        "item_stats": [
            "damage", "defense", "mana", "crit", "critical",
            "knockback", "sell", "buy", "rarity", "rare",
            "stat", "stats", "speed", "use time", "value", "tooltip",
            "obrazen", "obron", "atak", "statyst", "wartosc", "sprzedaz",
            "dzial", "dzialanie", "effect", "effects", "works", "work",
            "use", "used for", "what do", "what does", "do they do",
            "does it do", "what does it do", "what do they do",
            "ability", "abilities"
        ],
        "wiki": [
            "co to", "czym jest", "opisz", "opis",
            "tell me", "describe", "what is"
        ]
    }

    def detect_question_types(self, question: str):
        q = self.normalize_for_matching(question)
        matched_types = []
        for question_type, keywords in self.QUESTION_TYPES.items():
            if any(keyword in q for keyword in keywords):
                matched_types.append(question_type)
        if not matched_types:
            matched_types.append("wiki")
        return matched_types

    def find_best_item(self, question: str, threshold: int = 65, allow_fuzzy: bool = True):
        question_normalized = self.normalize_for_matching(question)
        exact_candidates = [
            normalized_name
            for normalized_name in self.normalized_item_name_keys
            if normalized_name in question_normalized
        ]
        
        if exact_candidates:
            best_exact = max(exact_candidates, key=len)
            return self.normalized_item_names[best_exact]
            
        if not allow_fuzzy:
            return None
            
        item_query = self.strip_question_words(question)
        if not item_query:
            return None
            
        item_query_no_spaces = item_query.replace(" ", "")
        
        match_1 = process.extractOne(item_query, self.item_alias_keys, scorer=fuzz.WRatio)
        match_2 = process.extractOne(item_query_no_spaces, self.item_alias_keys, scorer=fuzz.WRatio)
        matches = [m for m in [match_1, match_2] if m is not None]
        
        if not matches:
            return None
            
        matched_alias, score, index = max(matches, key=lambda x: x[1])
        if score < threshold:
            return None
            
        return self.item_aliases[matched_alias]

    def strip_wiki_question_words(self, question: str):
        stopwords = {
            "what", "is", "are", "the", "a", "an",
            "tell", "me", "about", "describe", "please",
            "co", "to", "czym", "jest", "opisz", "opis"
        }
        normalized = self.normalize_for_matching(question)
        words = [
            word for word in normalized.split()
            if word not in stopwords and len(word) > 1
        ]
        return " ".join(words)

    def is_loot_question(self, question: str):
        q = self.normalize_for_matching(question)
        loot_keywords = [
            "drop", "drops", "loot", "get from", "obtain from",
            "open", "opening", "crate", "crates",
            "chest", "chests", "contain", "contains",
            "content", "contents", "reward", "rewards"
        ]
        return any(keyword in q for keyword in loot_keywords)

    def find_best_wiki_title(self, question: str, threshold: int = 92):
        q = self.normalize_for_matching(question)
        query = self.strip_wiki_question_words(question)
        if not query:
            query = q
            
        exact_matches = [
            title_key for title_key in self.wiki_title_keys
            if title_key in q and (len(title_key) >= 6 or len(title_key.split()) >= 2)
        ]
        
        if exact_matches:
            best_key = max(exact_matches, key=lambda key: (len(key.split()), len(key)))
            return self.wiki_title_lookup[best_key]
            
        candidate_titles = [t for t in self.wiki_title_keys if len(t) >= 5]
        match = process.extractOne(query, candidate_titles, scorer=fuzz.WRatio)
        if match is None:
            return None
            
        matched_key, score, index = match
        if score < threshold:
            return None
            
        return self.wiki_title_lookup[matched_key]

    def search_wiki_by_title(self, question: str, k: int = 3):
        title = self.find_best_wiki_title(question)
        if not title:
            return []
            
        docs = []
        for metadata_field in ["title", "page"]:
            data = self.wiki_db._collection.get(
                where={metadata_field: {"$eq": title}},
                include=["metadatas", "documents"]
            )
            for metadata, document in zip(data["metadatas"], data["documents"]):
                docs.append(Document(page_content=document, metadata=metadata))
            if docs:
                break
                
        def chunk_number(doc):
            try:
                return int(doc.metadata.get("chunk", 999999))
            except Exception:
                return 999999
                
        docs = sorted(docs, key=chunk_number)
        return docs[:k]

    def search_wiki(self, question: str, k: int = 5):
        title_docs = self.search_wiki_by_title(question, k=3)
        if title_docs:
            return title_docs
        wiki_query = f"{question} Terraria wiki article overview main page"
        return self.wiki_db.similarity_search(wiki_query, k=k)

    def get_structured_docs(self, question_type: str, item_name: str | None = None, k: int = 10):
        data = self.structured_db._collection.get(
            where={"type": {"$eq": question_type}},
            include=["metadatas", "documents"]
        )
        docs = []
        for metadata, document in zip(data["metadatas"], data["documents"]):
            if item_name and metadata.get("item_name") != item_name:
                continue
            docs.append(Document(page_content=document, metadata=metadata))
            
        if question_type == "recipe":
            current_docs = [doc for doc in docs if str(doc.metadata.get("legacy", "")) == "0"]
            if current_docs:
                docs = current_docs
                
        return docs[:k]

    def deduplicate_docs(self, docs):
        seen = set()
        unique_docs = []
        for doc in docs:
            key = (
                doc.metadata.get("source", ""),
                doc.metadata.get("type", ""),
                doc.metadata.get("item_name", ""),
                doc.page_content[:200]
            )
            if key in seen:
                continue
            seen.add(key)
            unique_docs.append(doc)
        return unique_docs

    def retrieve_context(self, question: str, k: int = 10):
        detected_types = self.detect_question_types(question)
        loot_question = self.is_loot_question(question)
        
        structured_types = [
            t for t in detected_types
            if t in ["recipe", "item_stats"]
        ]
        
        if loot_question:
            structured_types = []
            
        if structured_types:
            item_name = self.find_best_item(question, allow_fuzzy=True)
        else:
            item_name = self.find_best_item(question, allow_fuzzy=False)
            
        docs = []
        if item_name and not structured_types and not loot_question:
            structured_types = ["item_stats"]
            
        if structured_types:
            for question_type in structured_types:
                docs += self.get_structured_docs(
                    question_type=question_type,
                    item_name=item_name,
                    k=k
                )
                
        if not docs:
            docs += self.search_wiki(question, k=5)
            
        docs = self.deduplicate_docs(docs)
        used_types = structured_types if docs and structured_types else ["wiki"]
        return docs, item_name, used_types

    @staticmethod
    def clean_structured_text(text: str):
        replacements = [
            ("Result amount:", "\nResult amount:"),
            ("Ingredients:", "\nIngredients:"),
            ("Crafting station:", "\nCrafting station:"),
            ("Legacy recipe:", "\nLegacy recipe:"),
            ("Version:", "\nVersion:"),
            ("name:", "\nname:"),
            ("itemid:", "\nitemid:"),
            ("internalname:", "\ninternalname:"),
            ("type:", "\ntype:"),
            ("tag:", "\ntag:"),
            ("rare:", "\nrare:"),
            ("sell:", "\nsell:"),
            ("tooltip:", "\ntooltip:"),
            ("damage:", "\ndamage:"),
            ("damagetype:", "\ndamagetype:"),
            ("defense:", "\ndefense:"),
            ("knockback:", "\nknockback:"),
            ("critical:", "\ncritical:"),
            ("usetime:", "\nusetime:"),
            ("mana:", "\nmana:"),
            ("velocity:", "\nvelocity:"),
            ("consumable:", "\nconsumable:"),
            ("placeable:", "\nplaceable:"),
        ]
        for old, new in replacements:
            text = text.replace(old, new)
            
        lines = [
            line for line in text.splitlines()
            if line.strip() and not line.strip().endswith(":")
        ]
        return "\n".join(lines).strip()

    @staticmethod
    def detect_amount(question: str):
        match = re.search(r"\b\d+\b", question)
        if match:
            return int(match.group())
        return 1

    @staticmethod
    def parse_number(value, default=1):
        match = re.search(r"\d+", str(value))
        if match:
            return int(match.group())
        return default

    @staticmethod
    def parse_single_ingredient(raw: str):
        raw = str(raw).strip()
        if not raw:
            return None
            
        match = re.match(r"^(\d+)\s*x?\s+(.+)$", raw, flags=re.IGNORECASE)
        if match:
            amount = int(match.group(1))
            name = match.group(2).strip()
            trailing = re.match(r"^(.+?)(\d+)$", name)
            if trailing and int(trailing.group(2)) == amount:
                name = trailing.group(1).strip()
            return name, amount
            
        match = re.match(r"^(.+?)\s*x\s*(\d+)$", raw, flags=re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            amount = int(match.group(2))
            return name, amount
            
        match = re.match(r"^(.+?)(\d+)$", raw)
        if match:
            name = match.group(1).strip()
            amount = int(match.group(2))
            return name, amount
            
        return raw, 1

    def parse_ingredients(self, line: str):
        ingredients_text = line.replace("Ingredients:", "").strip()
        if not ingredients_text:
            return []
            
        parts = [
            ing.strip()
            for ing in re.split(r"\s*\^\s*|\s*,\s*|\s*;\s*", ingredients_text)
            if ing.strip()
        ]
        
        parsed = []
        for part in parts:
            ingredient = self.parse_single_ingredient(part)
            if ingredient:
                parsed.append(ingredient)
        return parsed

    def structured_docs_to_facts(self, docs, question: str):
        requested_amount = self.detect_amount(question)
        facts = [f"Requested final item amount: {requested_amount}"]
        
        for option_index, doc in enumerate(docs, start=1):
            doc_type = doc.metadata.get("type", "")
            item_name = doc.metadata.get("item_name", "")
            legacy = doc.metadata.get("legacy", "")
            text = self.clean_structured_text(doc.page_content)
            
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            result_amount = 1
            for line in lines:
                if line.startswith("Result amount:"):
                    result_amount = self.parse_number(line, default=1)
                    
            crafts_needed = (requested_amount + result_amount - 1) // result_amount
            facts.append("")
            facts.append(f"Item: {item_name}")
            facts.append(f"Data type: {doc_type}")
            
            if doc_type == "recipe":
                facts.append(f"Recipe option: {option_index}")
                facts.append(f"Result amount per craft: {result_amount}")
                facts.append(f"Crafts needed for requested amount: {crafts_needed}")
                
            if legacy != "":
                facts.append(f"Legacy: {legacy}")
                
            for line in lines:
                if line.startswith("Recipe for:"):
                    facts.append(line)
                elif line.startswith("Ingredients:"):
                    ingredients = self.parse_ingredients(line)
                    facts.append("Ingredients per craft:")
                    for ingredient_name, ingredient_amount in ingredients:
                        facts.append(f"- {ingredient_amount}x {ingredient_name}")
                        
                    facts.append(f"Total ingredients for {requested_amount} requested item(s):")
                    for ingredient_name, ingredient_amount in ingredients:
                        total_amount = ingredient_amount * crafts_needed
                        facts.append(f"- {total_amount}x {ingredient_name}")
                elif line.startswith("Crafting station:"):
                    station = line.replace("Crafting station:", "").strip()
                    facts.append(f"Crafting station: {station}")
                elif line.startswith("tooltip:"):
                    tooltip = line.replace("tooltip:", "").strip()
                    facts.append(f"Effects: {tooltip}")
                elif line.startswith("sell:"):
                    sell = line.replace("sell:", "").strip()
                    facts.append(f"Sell value: {sell}")
                elif line.startswith("rare:"):
                    rare = line.replace("rare:", "").strip()
                    facts.append(f"Rarity: {rare}")
                elif line.startswith("damage:"):
                    damage = line.replace("damage:", "").strip()
                    facts.append(f"Damage: {damage}")
                elif line.startswith("damagetype:"):
                    damage_type = line.replace("damagetype:", "").strip()
                    facts.append(f"Damage type: {damage_type}")
                elif line.startswith("defense:"):
                    defense = line.replace("defense:", "").strip()
                    facts.append(f"Defense: {defense}")
                elif line.startswith("knockback:"):
                    knockback = line.replace("knockback:", "").strip()
                    facts.append(f"Knockback: {knockback}")
                elif line.startswith("critical:"):
                    critical = line.replace("critical:", "").strip()
                    facts.append(f"Critical chance: {critical}")
                elif line.startswith("velocity:"):
                    velocity = line.replace("velocity:", "").strip()
                    facts.append(f"Velocity: {velocity}")
                elif line.startswith("type:"):
                    item_type = line.replace("type:", "").strip()
                    facts.append(f"Type: {item_type}")
                elif line.startswith("tag:"):
                    tag = line.replace("tag:", "").strip()
                    facts.append(f"Tag: {tag}")
                    
        return "\n".join(facts).strip()

    def ask(self, question: str):
        if self.state != "READY":
            return {
                "answer": "Engine is not initialized yet. Please complete the initialization steps first.",
                "used_types": ["none"],
                "item_name": None,
                "sources": []
            }
            
        docs, item_name, used_types = self.retrieve_context(question)
        if not docs:
            return {
                "answer": "I cannot answer this based on the provided text.",
                "used_types": used_types,
                "item_name": item_name,
                "sources": []
            }
            
        is_structured = any(
            t in used_types
            for t in ["recipe", "item_stats"]
        )
        
        if is_structured:
            facts = self.structured_docs_to_facts(docs, question)
            answer = self.structured_chain.invoke({
                "question": question,
                "context": facts
            })
            context_to_send = facts
        else:
            context = "\n\n".join(
                f"SOURCE: {doc.metadata}\n{doc.page_content}"
                for doc in docs
            )
            answer = self.chain.invoke({
                "question": question,
                "context": context
            })
            context_to_send = context
            
        sources = [
            {
                "metadata": doc.metadata,
                "content": self.clean_structured_text(doc.page_content) if is_structured else doc.page_content
            }
            for doc in docs
        ]
        
        return {
            "answer": answer,
            "used_types": used_types,
            "item_name": item_name,
            "sources": sources,
            "raw_context": context_to_send
        }
