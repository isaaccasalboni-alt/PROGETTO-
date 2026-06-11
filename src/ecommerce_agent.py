import json
import os
import uuid
import requests
from datetime import datetime
from pathlib import Path

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

DATA_DIR = Path(__file__).parent.parent / "data"
CATALOG_FILE = DATA_DIR / "catalog.json"
ORDERS_FILE = DATA_DIR / "orders.json"

SHOP_NAME = os.getenv("SHOP_NAME", "Il Mio Negozio Online")
SHOP_CURRENCY = os.getenv("SHOP_CURRENCY", "EUR")

SYSTEM_PROMPT = f"""Sei un assistente e-commerce professionale per {SHOP_NAME}.
Aiuti il proprietario del negozio a gestire prodotti, ordini e strategie di vendita.

CAPACITÀ PRINCIPALI:
- Gestione catalogo prodotti (aggiunta, modifica, eliminazione, ricerca)
- Gestione ordini (creazione, aggiornamento stato, visualizzazione)
- Report e statistiche di vendita
- Generazione descrizioni prodotto SEO-ottimizzate
- Consigli su marketing, pricing, promozioni

REGOLE:
- Rispondi sempre in italiano
- Sii conciso ma completo
- Usa elenchi puntati per informazioni multiple
- Dopo ogni operazione conferma cosa hai fatto e mostra i dati rilevanti
- Se mancano informazioni necessarie, chiedi prima di procedere
- I prezzi sono in {SHOP_CURRENCY}
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_products",
            "description": "Elenca i prodotti del catalogo, opzionalmente filtrati per categoria o testo",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Filtra per categoria"},
                    "search": {"type": "string", "description": "Cerca per nome o descrizione"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_product",
            "description": "Aggiunge un nuovo prodotto al catalogo",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Nome del prodotto"},
                    "price": {"type": "number", "description": "Prezzo di vendita"},
                    "category": {"type": "string", "description": "Categoria del prodotto"},
                    "description": {"type": "string", "description": "Descrizione del prodotto"},
                    "stock": {"type": "integer", "description": "Quantità in magazzino"},
                    "sku": {"type": "string", "description": "Codice SKU (auto-generato se vuoto)"},
                },
                "required": ["name", "price", "category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_product",
            "description": "Aggiorna i campi di un prodotto esistente (prezzo, stock, descrizione, ecc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "ID o SKU del prodotto"},
                    "name": {"type": "string"},
                    "price": {"type": "number"},
                    "category": {"type": "string"},
                    "description": {"type": "string"},
                    "stock": {"type": "integer"},
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_product",
            "description": "Elimina un prodotto dal catalogo",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "ID o SKU del prodotto"},
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_orders",
            "description": "Elenca gli ordini, filtrabili per stato",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filtra per stato: nuovo, in_lavorazione, spedito, consegnato, annullato",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_order",
            "description": "Crea un nuovo ordine",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "customer_email": {"type": "string"},
                    "items": {
                        "type": "array",
                        "description": "Prodotti ordinati con ID e quantità",
                        "items": {
                            "type": "object",
                            "properties": {
                                "product_id": {"type": "string"},
                                "quantity": {"type": "integer"},
                            },
                        },
                    },
                    "notes": {"type": "string"},
                },
                "required": ["customer_name", "customer_email", "items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_order_status",
            "description": "Aggiorna lo stato di un ordine",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "ID ordine (es. ORD-0001)"},
                    "status": {
                        "type": "string",
                        "description": "Nuovo stato: nuovo, in_lavorazione, spedito, consegnato, annullato",
                    },
                },
                "required": ["order_id", "status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sales_report",
            "description": "Genera statistiche di vendita aggregate (fatturato, ordini per stato, prodotti)",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_product_description",
            "description": "Genera una descrizione SEO-ottimizzata per un prodotto",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {"type": "string"},
                    "category": {"type": "string"},
                    "features": {"type": "string", "description": "Caratteristiche principali del prodotto"},
                    "tone": {
                        "type": "string",
                        "enum": ["professionale", "amichevole", "luxury"],
                        "description": "Tono della descrizione",
                    },
                },
                "required": ["product_name", "category"],
            },
        },
    },
]


# ──── Persistenza dati ────────────────────────────────────────────────────────

def _load(path: Path) -> list:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def _save(path: Path, data: list) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ──── Operazioni catalogo ────────────────────────────────────────────────────

def list_products(category: str = None, search: str = None) -> dict:
    products = _load(CATALOG_FILE)
    if category:
        products = [p for p in products if p.get("category", "").lower() == category.lower()]
    if search:
        q = search.lower()
        products = [p for p in products if q in p.get("name", "").lower() or q in p.get("description", "").lower()]
    return {"products": products, "total": len(products)}


def add_product(name: str, price: float, category: str, description: str = "", stock: int = 0, sku: str = "") -> dict:
    products = _load(CATALOG_FILE)
    product = {
        "id": str(uuid.uuid4())[:8],
        "sku": sku or f"SKU-{len(products) + 1:04d}",
        "name": name,
        "price": round(float(price), 2),
        "category": category,
        "description": description,
        "stock": int(stock),
        "created_at": datetime.now().isoformat(),
    }
    products.append(product)
    _save(CATALOG_FILE, products)
    return {"success": True, "product": product}


def update_product(product_id: str, updates: dict) -> dict:
    products = _load(CATALOG_FILE)
    for i, p in enumerate(products):
        if p["id"] == product_id or p.get("sku") == product_id:
            products[i].update({k: v for k, v in updates.items() if v is not None})
            products[i]["updated_at"] = datetime.now().isoformat()
            _save(CATALOG_FILE, products)
            return {"success": True, "product": products[i]}
    return {"success": False, "error": f"Prodotto '{product_id}' non trovato"}


def delete_product(product_id: str) -> dict:
    products = _load(CATALOG_FILE)
    filtered = [p for p in products if p["id"] != product_id and p.get("sku") != product_id]
    if len(filtered) < len(products):
        _save(CATALOG_FILE, filtered)
        return {"success": True, "deleted_id": product_id}
    return {"success": False, "error": f"Prodotto '{product_id}' non trovato"}


# ──── Operazioni ordini ──────────────────────────────────────────────────────

def list_orders(status: str = None) -> dict:
    orders = _load(ORDERS_FILE)
    if status:
        orders = [o for o in orders if o.get("status", "").lower() == status.lower()]
    return {"orders": orders, "total": len(orders)}


def add_order(customer_name: str, customer_email: str, items: list, notes: str = "") -> dict:
    orders = _load(ORDERS_FILE)
    catalog = {p["id"]: p for p in _load(CATALOG_FILE)}
    catalog.update({p["sku"]: p for p in _load(CATALOG_FILE)})

    total = 0.0
    order_items = []
    for item in items:
        pid = item.get("product_id", "")
        qty = int(item.get("quantity", 1))
        product = catalog.get(pid)
        if not product:
            return {"success": False, "error": f"Prodotto '{pid}' non trovato nel catalogo"}
        subtotal = round(product["price"] * qty, 2)
        total += subtotal
        order_items.append({
            "product_id": product["id"],
            "name": product["name"],
            "price": product["price"],
            "quantity": qty,
            "subtotal": subtotal,
        })

    order = {
        "id": f"ORD-{len(orders) + 1:04d}",
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": order_items,
        "total": round(total, 2),
        "status": "nuovo",
        "notes": notes,
        "created_at": datetime.now().isoformat(),
    }
    orders.append(order)
    _save(ORDERS_FILE, orders)
    return {"success": True, "order": order}


def update_order_status(order_id: str, status: str) -> dict:
    orders = _load(ORDERS_FILE)
    for i, o in enumerate(orders):
        if o["id"] == order_id:
            orders[i]["status"] = status
            orders[i]["updated_at"] = datetime.now().isoformat()
            _save(ORDERS_FILE, orders)
            return {"success": True, "order": orders[i]}
    return {"success": False, "error": f"Ordine '{order_id}' non trovato"}


def get_sales_report() -> dict:
    orders = _load(ORDERS_FILE)
    products = _load(CATALOG_FILE)
    total_revenue = sum(o.get("total", 0) for o in orders if o.get("status") != "annullato")
    by_status: dict = {}
    for o in orders:
        s = o.get("status", "sconosciuto")
        by_status[s] = by_status.get(s, 0) + 1
    top_products: dict = {}
    for o in orders:
        if o.get("status") == "annullato":
            continue
        for item in o.get("items", []):
            name = item.get("name", "?")
            top_products[name] = top_products.get(name, 0) + item.get("quantity", 0)
    top = sorted(top_products.items(), key=lambda x: x[1], reverse=True)[:5]
    low_stock = [p for p in products if p.get("stock", 0) <= 5]
    return {
        "total_orders": len(orders),
        "total_revenue": round(total_revenue, 2),
        "currency": SHOP_CURRENCY,
        "by_status": by_status,
        "top_products": [{"name": n, "units_sold": u} for n, u in top],
        "low_stock_products": [{"id": p["id"], "name": p["name"], "stock": p["stock"]} for p in low_stock],
        "products_in_catalog": len(products),
    }


# ──── Agente ─────────────────────────────────────────────────────────────────

class EcommerceAgent:
    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY", "")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY non impostata nel .env")
        self.history: list[dict] = []

    def chat(self, user_message: str) -> str:
        self.history.append({"role": "user", "content": user_message})
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self.history

        response = self._call_groq(messages, tools=TOOLS, tool_choice="auto")
        assistant_msg = response["choices"][0]["message"]

        # Gestione chiamate agli strumenti (può essere iterativa)
        while assistant_msg.get("tool_calls"):
            self.history.append(assistant_msg)
            for tc in assistant_msg["tool_calls"]:
                func_name = tc["function"]["name"]
                try:
                    func_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    func_args = {}
                result = self._execute_tool(func_name, func_args)
                self.history.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                })

            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self.history
            response = self._call_groq(messages, tools=TOOLS)
            assistant_msg = response["choices"][0]["message"]

        final_text = assistant_msg.get("content") or ""
        self.history.append({"role": "assistant", "content": final_text})
        return final_text

    def reset(self) -> None:
        self.history = []

    def _call_groq(self, messages: list, tools: list = None, tool_choice: str = None) -> dict:
        payload: dict = {
            "model": GROQ_MODEL,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        if tools:
            payload["tools"] = tools
        if tool_choice:
            payload["tool_choice"] = tool_choice

        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=60,
        )
        if not resp.ok:
            raise RuntimeError(f"Errore Groq {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    def _execute_tool(self, name: str, args: dict) -> dict:
        try:
            if name == "list_products":
                return list_products(**args)
            if name == "add_product":
                return add_product(**args)
            if name == "update_product":
                product_id = args.pop("product_id")
                return update_product(product_id, args)
            if name == "delete_product":
                return delete_product(**args)
            if name == "list_orders":
                return list_orders(**args)
            if name == "add_order":
                return add_order(**args)
            if name == "update_order_status":
                return update_order_status(**args)
            if name == "get_sales_report":
                return get_sales_report()
            if name == "generate_product_description":
                return self._generate_description(**args)
            return {"error": f"Funzione '{name}' non riconosciuta"}
        except Exception as e:
            return {"error": str(e)}

    def _generate_description(self, product_name: str, category: str, features: str = "", tone: str = "professionale") -> dict:
        tone_map = {
            "professionale": "formale, preciso, orientato ai benefici",
            "amichevole": "caldo, colloquiale, entusiasta",
            "luxury": "esclusivo, elegante, aspirazionale",
        }
        tone_desc = tone_map.get(tone, tone_map["professionale"])
        prompt = (
            f"Genera una descrizione prodotto SEO-ottimizzata per un e-commerce.\n\n"
            f"Prodotto: {product_name}\n"
            f"Categoria: {category}\n"
            f"Caratteristiche: {features or 'generali'}\n"
            f"Tono: {tone_desc}\n\n"
            f"La descrizione deve essere 150-250 parole, con bullet point dei punti di forza e CTA finale.\n"
            f"Rispondi SOLO con la descrizione, in italiano."
        )
        payload = {
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.85,
            "max_tokens": 600,
        }
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=30,
        )
        if not resp.ok:
            return {"error": f"Errore generazione descrizione: {resp.status_code}"}
        description = resp.json()["choices"][0]["message"]["content"].strip()
        return {"description": description, "product_name": product_name}
