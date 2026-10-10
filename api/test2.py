from collections import defaultdict
import json,re
from pathlib import Path
from flask import Flask,render_template_string,redirect,url_for
import os
from admin_auth import admin_bp

app=Flask(__name__)
BASE_DIR=Path(__file__).resolve().parent.parent
DATA_FILE=BASE_DIR/"data"/"menu.json"
BUFFET_CATEGORIES=["Main Course","Raita","Dal","Rice","Breads","Paneer","Vegetables","Desserts","Starter"]
BUFFET_PRICE={"indoor":500,"outdoor":550}
BUFFET_MIN_PERSONS=60
MAX_QTY=12

app.secret_key = os.environ.get("FLASK_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY environment variable is missing.")

app.register_blueprint(admin_bp)


def slugify(text):
    text=re.sub(r"[^\w\s-]","",str(text).lower())
    return re.sub(r"[-\s]+","-",text).strip("-")

def load_menu():
    empty={"menu_items":[],"buffet_items":[],"buffet_addons":[]}
    if not DATA_FILE.exists(): return empty
    with open(DATA_FILE,"r",encoding="utf-8") as f: data=json.load(f)
    if isinstance(data,list): return {**empty,"menu_items":data}
    return {"menu_items":data.get("menu_items",[]),
            "buffet_items":data.get("buffet_items",[]),
            "buffet_addons":data.get("buffet_addons",[])}

def build_menu(order_type):
    fields={"dinein":("dine_in_price","dine_in_active"),"parcel":("pickup_price","pickup_active")}
    if order_type not in fields: order_type="parcel"
    price_field,active_field=fields[order_type]
    categories=defaultdict(list)
    for item in load_menu()["menu_items"]:
        if not item.get("is_active",True) or not item.get(active_field,True): continue
        price=item.get(price_field)
        if price is None or float(price)<=0: continue
        x=dict(item)
        x["slug"]=slugify(item.get("item_name",""))
        x["price"]=float(price)
        categories[item.get("category","Other")].append(x)
    return categories

def build_buffet_menu():
    categories={c:[] for c in BUFFET_CATEGORIES}
    for item in load_menu()["buffet_items"]:
        if not item.get("is_active",True): continue
        category=str(item.get("category","")).strip()
        if category not in categories: continue
        x=dict(item)
        x["slug"]=slugify(str(item.get("id",item.get("item_name","")))+"-"+item.get("item_name",""))
        categories[category].append(x)
    return categories

def build_buffet_addons():
    addons=[]
    for item in load_menu()["buffet_addons"]:
        if not item.get("is_active",True): continue
        try: price=float(item.get("price",0))
        except (TypeError,ValueError): continue
        if price<=0: continue
        addons.append({
            "id":str(item.get("id",slugify(item.get("item_name","")))),
            "item_name":item.get("item_name",""),
            "description":item.get("description",""),
            "price":price,
        })
    return addons

MENU_TEMPLATE="""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{{ title }} | Vrindavan Dhaba Testing</title>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700;800;900&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
<style>
:root{--bg:#fdfbf7;--primary:#4a0e17;--deep:#33080e;--amber:#c86a28;--gold:#d4af37;--green:#25d366;--text:#2c1810;--muted:#7a6258;--soft:#fff5ec;--goldbg:#faf5e8;--shadow:0 4px 18px rgba(74,14,23,.06);--elevated:0 10px 28px rgba(51,8,14,.16)}
body{background:var(--bg);font-family:'Plus Jakarta Sans',sans-serif;color:var(--text);padding-bottom:110px;-webkit-tap-highlight-color:transparent}
.hero-banner{background:linear-gradient(135deg,var(--deep),var(--primary));color:#fff;padding:28px 20px 32px;border-radius:0 0 24px 24px;position:relative;box-shadow:var(--elevated)}
.hero-banner:after{content:'';position:absolute;bottom:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--gold),var(--amber))}
.brand-header{font-family:'Cinzel',serif;font-weight:900;color:var(--gold);font-size:1.8rem;letter-spacing:1.2px;margin:0;text-shadow:0 2px 6px rgba(0,0,0,.4)}
.status-pill{background:rgba(255,255,255,.12);backdrop-filter:blur(8px);border:1px solid rgba(212,175,55,.4);padding:5px 14px;border-radius:30px;font-size:.78rem;color:#fff5ec;display:inline-flex;align-items:center;gap:6px;font-weight:600}
.mode-container{margin-top:-22px;padding:0 12px;position:relative;z-index:10}
.mode-switch{background:#fff;border-radius:20px;padding:6px;display:flex;box-shadow:var(--elevated);border:1.5px solid var(--gold)}
.mode-btn{flex:1;text-align:center;text-decoration:none;padding:10px 8px;border-radius:14px;font-size:.85rem;font-weight:700;color:var(--primary);display:flex;align-items:center;justify-content:center;gap:6px}
.mode-btn.active{background:var(--primary);color:var(--gold);box-shadow:0 4px 12px rgba(74,14,23,.3)}
.search-box{position:relative;margin:20px 0 14px}
.search-box input{background:#fff;border:1.5px solid rgba(212,175,55,.5);border-radius:18px;padding:12px 16px 12px 44px;font-size:.92rem;color:var(--text);box-shadow:var(--shadow)}
.search-box input:focus{border-color:var(--amber);box-shadow:0 0 0 4px rgba(200,106,40,.18);outline:none}
.search-box i{position:absolute;left:16px;top:50%;transform:translateY(-50%);color:var(--amber);font-size:1.05rem}
.category-scroll-wrapper{position:sticky;top:0;z-index:1020;background:rgba(253,251,247,.96);padding:10px 0;margin:0 -12px 16px;border-bottom:1px solid rgba(212,175,55,.25);backdrop-filter:blur(12px)}
.category-scroll{display:flex;gap:8px;overflow-x:auto;padding:0 16px;scrollbar-width:none;scroll-behavior:smooth}
.category-scroll::-webkit-scrollbar{display:none}
.cat-chip{white-space:nowrap;padding:8px 18px;border-radius:20px;background:#fff;border:1.5px solid rgba(212,175,55,.6);font-size:.82rem;font-weight:700;color:var(--primary);text-decoration:none;box-shadow:var(--shadow)}
.cat-chip.active{background:var(--amber);color:#fff;border-color:var(--amber)}
.accordion-item{background:transparent;border:none;margin-bottom:12px}
.accordion-button{background:#fff;border:1.5px solid rgba(212,175,55,.5);border-radius:18px!important;font-family:'Cinzel',serif;font-size:1.05rem;font-weight:800;color:var(--primary);box-shadow:var(--shadow);padding:17px 20px;transition:.2s}
.accordion-button:not(.collapsed){background:var(--goldbg);color:var(--primary);box-shadow:none;border-color:var(--gold)}
.accordion-button:focus{box-shadow:0 0 0 3px rgba(200,106,40,.12)}
.accordion-button:after{background-size:1rem}
.cat-count-badge{background:var(--primary);color:var(--gold);font-size:.75rem;font-weight:800;padding:4px 10px;border-radius:12px}
.accordion-body{padding:10px 0 0}
.food-card{background:#fff;border-radius:18px;padding:14px;margin-bottom:10px;border:1px solid rgba(212,175,55,.3);box-shadow:var(--shadow);display:flex;justify-content:space-between;gap:10px}
.food-type-icon{width:16px;height:16px;border-radius:4px;display:inline-flex;align-items:center;justify-content:center;padding:2px;flex-shrink:0}
.food-type-icon.veg{border:2px solid #2e7d32}
.food-type-icon.veg:after{content:'';width:6px;height:6px;background:#2e7d32;border-radius:50%}
.popular-tag{font-size:.68rem;background:var(--soft);color:var(--amber);font-weight:800;padding:2px 8px;border-radius:6px;display:inline-flex;align-items:center;gap:3px;border:1px solid rgba(200,106,40,.3)}
.food-name{font-weight:700;font-size:.98rem;color:var(--primary);margin-top:4px}
.food-desc{font-size:.8rem;color:var(--muted);margin-top:4px;line-height:1.4}
.card-action-side{display:flex;flex-direction:column;justify-content:space-between;align-items:flex-end;min-width:82px;flex-shrink:0}
.price-text{font-size:1.05rem;font-weight:800;color:var(--primary)}
.add-btn{background:var(--soft);border:1.5px solid var(--amber);color:var(--amber);font-weight:800;font-size:.78rem;padding:6px 16px;border-radius:12px;cursor:pointer;pointer-events:auto;position:relative;z-index:5;min-width:64px}
.add-btn:active{transform:scale(.95)}
.qty-controls{display:none;align-items:center;background:var(--primary);color:#fff;border-radius:12px;padding:2px;box-shadow:0 4px 10px rgba(74,14,23,.2)}
.qty-btn{background:none;border:none;color:var(--gold);width:28px;height:28px;font-weight:800;display:flex;align-items:center;justify-content:center;cursor:pointer}
.qty-val{font-size:.85rem;font-weight:700;padding:0 6px;color:#fff}
.qty-limit{font-size:.65rem;color:var(--amber);font-weight:700;margin-top:3px}
.cart-float-bar{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);width:calc(100% - 32px);max-width:600px;background:var(--primary);border:1.5px solid var(--gold);color:#fff;border-radius:20px;padding:12px 20px;display:none;justify-content:space-between;align-items:center;box-shadow:var(--elevated);z-index:1030}
.view-cart-btn{background:var(--amber);color:#fff;border:none;font-weight:800;font-size:.85rem;padding:8px 18px;border-radius:12px;cursor:pointer}
.offcanvas-bottom{height:auto!important;max-height:85vh;border-top-left-radius:28px;border-top-right-radius:28px;background:var(--bg);z-index:1060!important}
.cart-modal-header{border-bottom:1px solid rgba(212,175,55,.3);padding:18px 20px}
.cart-modal-body{padding:16px 20px 30px;overflow-y:auto;max-height:calc(85vh - 70px)}
.cart-item-row{padding:14px 0;border-bottom:1px dashed rgba(212,175,55,.4)}
.cart-item-main{display:flex;justify-content:space-between;align-items:center;gap:10px}
.cart-note{margin-top:10px}
.cart-note-label{font-size:.75rem;font-weight:700;color:var(--muted);margin-bottom:5px;display:block}
.cart-note-input{width:100%;border:1px solid rgba(74,14,23,.12);border-radius:10px;padding:8px 10px;font-size:.8rem;background:#fff;color:var(--text);outline:none}
.bill-details{background:#fff;border:1px solid rgba(212,175,55,.5);border-radius:16px;padding:16px;margin-top:16px}
.bill-row{display:flex;justify-content:space-between;font-size:.88rem;margin-bottom:8px;color:var(--muted)}
.bill-row.total{font-size:1.05rem;font-weight:800;color:var(--primary);border-top:1px solid rgba(212,175,55,.3);padding-top:10px;margin-top:10px;margin-bottom:0}
.btn-call-order{background:var(--primary);color:#fff;border-radius:12px;font-weight:700;font-size:.88rem;padding:12px;border:none}
.btn-whatsapp-order{background:var(--green);color:#fff;border-radius:12px;font-weight:700;font-size:.88rem;padding:12px;border:none;text-decoration:none;display:flex;align-items:center;justify-content:center;gap:6px}
.customer-order-type{background:rgba(212,175,55,.08);border:1px solid rgba(212,175,55,.25)}
.customer-modal-input{border-radius:12px;padding:11px 13px;border:1px solid rgba(74,14,23,.18)}
.no-results{display:none;text-align:center;padding:40px 20px;color:var(--muted)}
.buffet-mode-card{background:#fff;border:1.5px solid rgba(212,175,55,.5);border-radius:20px;padding:18px;margin:20px 0;box-shadow:var(--shadow)}
.buffet-mode-title{font-family:'Cinzel',serif;font-weight:800;color:var(--primary);font-size:1.1rem}
.buffet-price{font-size:1.12rem;font-weight:800;color:var(--amber)}
.buffet-choice{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:13px;border:1.5px solid rgba(212,175,55,.4);border-radius:14px;margin-top:10px;background:#fffaf4}
.buffet-select-btn{background:var(--primary);color:#fff;border:0;border-radius:10px;padding:7px 13px;font-size:.78rem;font-weight:800}
.buffet-help{font-size:.78rem;color:var(--muted);line-height:1.45}
.buffet-option{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:9px 10px;border:1px solid rgba(212,175,55,.25);border-radius:10px;margin-bottom:7px;background:#fff}
.buffet-option.selected{background:var(--goldbg);border-color:var(--gold)}
.buffet-option-btn{border:1px solid var(--amber);background:var(--soft);color:var(--amber);border-radius:8px;padding:5px 9px;font-size:.72rem;font-weight:800}
.buffet-option-btn.selected{background:var(--primary);color:#fff;border-color:var(--primary)}
.buffet-additional{background:#fff7ed;border:1px dashed var(--amber);border-radius:12px;padding:10px;margin-top:10px}
.buffet-additional-item{display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:.78rem;padding:6px 0}
.buffet-plate{background:#fff;border:1.5px solid rgba(212,175,55,.5);border-radius:16px;padding:14px;margin-bottom:14px}
.buffet-plate-title{font-weight:800;color:var(--primary)}
.buffet-mini-category{margin-top:9px;font-size:.8rem}
.buffet-mini-category b{color:var(--primary)}
.buffet-add-extra{width:100%;background:var(--soft);color:var(--amber);border:1px solid var(--amber);border-radius:9px;padding:7px;font-size:.75rem;font-weight:800;margin-top:8px}
.buffet-limit-note{font-size:.7rem;color:var(--amber);font-weight:700;margin-top:3px}
</style>
</head>
<body>
<div class="hero-banner text-center">
<div class="d-flex justify-content-between align-items-center mb-2">
<span class="status-pill"><i class="bi bi-clock-fill me-1"></i>Open • 11 AM - 12 PM</span>
<div class="text-end px-3 pt-3"> <a href="/admin/login" class="btn btn-sm" style="background:#4a0e17;color:#d4af37; border:1px solid #d4af37;border-radius:10px; font-weight:800;padding:8px 14px;"> <i class="bi bi-shield-lock-fill me-1"></i> Admin Panel </a> </div>
<span class="status-pill"><i class="bi bi-star-fill me-1" style="color:var(--gold)"></i>4.9 (9.2k+)</span>
</div>
<h1 class="brand-header">🛕 VRINDAVAN DHABA Testing 2.0</h1>
<p class="small text-white-50 m-0 mt-1">Authentic Pure Vegetarian Culinary Experience</p>
</div>

<div class="container" style="max-width:640px">
<div class="mode-container">
<div class="mode-switch">
<a href="/dinein" class="mode-btn {{ 'active' if order_type=='dinein' else '' }}"><i class="bi bi-shop"></i>Dine In</a>
<a href="/parcel" class="mode-btn {{ 'active' if order_type=='parcel' else '' }}"><i class="bi bi-bag-check"></i>Parcel</a>
<a href="/buffet" class="mode-btn {{ 'active' if order_type=='buffet' else '' }}"><i class="bi bi-egg-fried"></i>Buffet</a>
</div>
</div>

{% if order_type=="buffet" %}
<div class="buffet-mode-card">
<div class="buffet-mode-title">🍽️ Buffet Selection</div>
<div class="buffet-help mt-1"><b>Minimum booking: {{ min_persons }} persons.</b> Select Indoor or Outdoor buffet. Main Course has no selection limit. Raita, Dal, Rice, Paneer, Vegetables, Starter and Desserts require one choice. Breads allows maximum two choices per plate.</div>
<div class="buffet-choice">
<div><div class="fw-bold" style="color:var(--primary)">🏠 Indoor Buffet</div><div class="buffet-help">Buffet at Vrindavan Dhaba</div><div class="buffet-price">₹500 / plate</div></div>
<button class="buffet-select-btn" type="button" onclick="selectBuffetMode('indoor')">SELECT</button>
</div>
<div class="buffet-choice">
<div><div class="fw-bold" style="color:var(--primary)">🌳 Outdoor Buffet</div><div class="buffet-help">Buffet at customer's location</div><div class="buffet-price">₹550 / plate</div></div>
<button class="buffet-select-btn" type="button" onclick="selectBuffetMode('outdoor')">SELECT</button>
</div>
</div>

<div id="buffetBuilder" style="display:none">
<div class="buffet-mode-card">
<div class="d-flex justify-content-between align-items-center">
<div><div class="buffet-mode-title" id="selectedBuffetTitle">Indoor Buffet</div><div class="buffet-help" id="selectedBuffetDescription"></div></div>
<div class="buffet-price" id="selectedBuffetPrice">₹500</div>
</div>
<div class="buffet-help mt-2"><b>Main Course:</b> choose any number.<br><b>Raita, Dal, Rice, Paneer, Vegetables, Starter & Desserts:</b> choose one each.<br><b>Breads:</b> choose up to two items.</div>
</div>

<div class="accordion" id="buffetAccordion">
{% for category,items in buffet_categories.items() %}
<div class="accordion-item category-group">
<h2 class="accordion-header">
<button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#buffet-collapse-{{ loop.index }}" aria-expanded="false">
<span class="cat-count-badge me-2">{{ items|length }}</span><span class="me-auto">{{ category }}</span>
</button>
</h2>
<div id="buffet-collapse-{{ loop.index }}" class="accordion-collapse collapse">
<div class="accordion-body">
{% if not items %}<div class="text-muted small p-3">No buffet items added to this category yet.</div>{% endif %}
{% for item in items %}
<div class="buffet-option" data-buffet-category="{{ category }}" data-buffet-id="{{ item.slug }}">
<div><div class="food-name">{{ item.item_name }}</div>{% if item.description %}<div class="food-desc">{{ item.description }}</div>{% endif %}</div>
<button class="buffet-option-btn" type="button" data-buffet-select="{{ item.slug }}" data-category="{{ category }}" data-name="{{ item.item_name }}">SELECT</button>
</div>
{% endfor %}
{% if category=="Breads" %}<div class="buffet-limit-note">Maximum 2 bread selections per plate.</div>{% endif %}
</div>
</div>
</div>
{% endfor %}
</div>
<button type="button" class="btn btn-whatsapp-order w-100 mt-2" id="addBuffetPlateBtn" onclick="addBuffetPlate()"><i class="bi bi-plus-circle me-1"></i>ADD BUFFET PLATE</button>
<div class="text-center small text-muted mt-2" id="buffetValidation"></div>
</div>

<div class="no-results" id="noResults"></div>
{% else %}

<div class="search-box">
<i class="bi bi-search"></i>
<input type="text" id="searchInput" class="form-control" placeholder="Search dish name, dal, paneer..." onkeyup="filterMenu()">
</div>

<div class="category-scroll-wrapper">
<div class="category-scroll" id="categoryScroll">
{% for category in categories.keys() %}
<a href="#cat-{{ loop.index }}" class="cat-chip {{ 'active' if loop.first else '' }}" onclick="setActiveChip(this)">{{ category }}</a>
{% endfor %}
</div>
</div>

<div class="text-center small text-muted mb-3">Tap a category to view dishes</div>

<div class="accordion" id="menuAccordion">
{% for category,items in categories.items() %}
<div class="accordion-item category-group" id="cat-{{ loop.index }}">
<h2 class="accordion-header">
<button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-{{ loop.index }}" aria-expanded="false">
<span class="cat-count-badge me-2">{{ items|length }}</span><span class="me-auto">{{ category }}</span>
</button>
</h2>
<div id="collapse-{{ loop.index }}" class="accordion-collapse collapse">
<div class="accordion-body">
{% for item in items %}
<div class="food-card" data-id="{{ item.slug }}" data-name="{{ item.item_name }}" data-price="{{ item.price }}">
<div class="flex-grow-1">
<div class="d-flex align-items-center gap-2">
<span class="food-type-icon veg"></span>
{% if item.popular %}<span class="popular-tag"><i class="bi bi-fire"></i>Bestseller</span>{% endif %}
</div>
<div class="food-name">{{ item.item_name }}</div>
<div class="food-desc">{{ item.description or 'Prepared with fresh ingredients and authentic dhaba spices.' }}</div>
</div>
<div class="card-action-side">
<div class="price-text">₹{{ "%.0f"|format(item.price) }}</div>
{% if order_type=="dinein" %}
<button class="add-btn" type="button" onclick="return false;">VIEW</button>
{% else %}
<button class="add-btn" type="button" data-action="add" data-id="{{ item.slug }}" data-name="{{ item.item_name }}" data-price="{{ item.price }}">ADD</button>
{% endif %}
<div class="qty-controls" id="qty-ctrl-{{ item.slug }}">
<button class="qty-btn" type="button" data-action="minus" data-id="{{ item.slug }}" data-name="{{ item.item_name }}" data-price="{{ item.price }}">−</button>
<span class="qty-val" id="qty-val-{{ item.slug }}">1</span>
<button class="qty-btn" type="button" data-action="plus" data-id="{{ item.slug }}" data-name="{{ item.item_name }}" data-price="{{ item.price }}">+</button>
</div>
<div class="qty-limit">Max 12</div>
</div>
</div>
{% endfor %}
</div>
</div>
</div>
{% endfor %}
</div>

<div class="no-results" id="noResults">
<i class="bi bi-search-heart display-4 text-muted"></i>
<h6 class="mt-3">No matching dishes found</h6>
<p class="small">Try searching for something else like "Paneer" or "Naan".</p>
</div>
{% endif %}
</div>

<div class="cart-float-bar" id="cartBar">
<div><div class="fw-bold" id="cartCount">0 ITEMS SELECTED</div><div class="small opacity-75" id="cartTotal">Total: ₹0</div></div>
<button class="view-cart-btn" type="button" data-bs-toggle="offcanvas" data-bs-target="#cartModal">VIEW ORDER <i class="bi bi-arrow-right ms-1"></i></button>
</div>

<div class="offcanvas offcanvas-bottom" tabindex="-1" id="cartModal">
<div class="cart-modal-header d-flex justify-content-between align-items-center">
<div><h5 class="m-0 fw-bold" style="color:var(--primary);font-family:'Cinzel',serif">Your Order Cart</h5><small class="text-muted" id="cartModeText">Order Mode: <b>{{ "Buffet" if order_type=="buffet" else ("Dine In" if order_type=="dinein" else "Parcel") }}</b></small></div>
<button type="button" class="btn-close" data-bs-dismiss="offcanvas"></button>
</div>
<div class="cart-modal-body">
<div id="cartItemsList"></div>
<div class="bill-details">
<div class="bill-row"><span>Items Subtotal</span><span id="billSubtotal">₹0</span></div>
<div class="bill-row"><span>Taxes & Charges already included (5%)</span><span id="billTax">₹0</span></div>
<div class="bill-row total"><span>Grand Total</span><span id="billGrandTotal">₹0</span></div>
</div>
<div class="mt-4 d-flex flex-column gap-2">
<button class="btn btn-call-order w-100" type="button" onclick="showCallOrderModal()"><i class="bi bi-telephone-fill me-1"></i>Call to Place Order</button>
<button class="btn btn-whatsapp-order w-100" type="button" onclick="startOrderProcess()"><i class="bi bi-whatsapp me-1"></i>Send Order on WhatsApp</button>
<button class="btn btn-sm text-muted mt-1" type="button" onclick="clearCart()">Clear Cart</button>
</div>
</div>
</div>

<div class="modal fade" id="callOrderModal" tabindex="-1">
<div class="modal-dialog modal-dialog-centered">
<div class="modal-content text-center p-4" style="border-radius:20px;border:1.5px solid var(--gold)">
<div class="modal-body p-0">
<i class="bi bi-telephone-outbound-fill display-4 mb-3 d-block" style="color:var(--primary)!important"></i>
<h5 class="fw-bold mb-2" style="color:var(--primary)">Call to Place Your Order</h5>
<p class="text-muted small mb-3">Please call us directly at the number below to confirm your order:</p>
<div class="p-3 mb-3" style="background:var(--goldbg);border-radius:12px;font-weight:800;font-size:1.2rem;color:var(--primary)">📞 8982003335</div>
<p class="small text-muted mb-4">Thanks for ordering from <b>Vrindavan Dhaba</b>!</p>
<a href="tel:+918982003335" class="btn text-white fw-bold w-100 py-2 mb-2" style="background:var(--primary);border-radius:12px"><i class="bi bi-telephone-fill me-1"></i>Call Now</a>
<button type="button" class="btn btn-light w-100 py-2" data-bs-dismiss="modal" style="border-radius:12px">Close</button>
</div>
</div>
</div>
</div>

<div class="modal fade" id="customerDetailsModal" tabindex="-1">
<div class="modal-dialog modal-dialog-centered modal-dialog-scrollable">
<div class="modal-content" style="border-radius:20px;border:1.5px solid var(--gold)">
<div class="modal-header" style="border-bottom:1px solid rgba(212,175,55,.3)">
<div><h5 class="modal-title fw-bold" style="color:var(--primary);font-family:'Cinzel',serif">Complete Your Order</h5><small class="text-muted">Just a few details to confirm your order</small></div>
<button type="button" class="btn-close" data-bs-dismiss="modal"></button>
</div>
<div class="modal-body">
<div class="customer-order-type mb-3 p-3 rounded-3"><div class="small text-muted">Order Type</div><div class="fw-bold" style="color:var(--primary)" id="customerOrderTypeLabel">🥡 Parcel</div></div>
<div class="mb-3"><label for="customerName" class="form-label fw-semibold">Your Name</label><input type="text" id="customerName" class="form-control customer-modal-input" placeholder="Enter your name" autocomplete="name"></div>
<div class="mb-3"><label for="customerMobile" class="form-label fw-semibold">Mobile Number</label><input type="tel" id="customerMobile" class="form-control customer-modal-input" placeholder="10-digit mobile number" maxlength="10" inputmode="numeric" autocomplete="tel"></div>
{% if order_type=="buffet" %}
<div class="mb-3"><label for="customerPersons" class="form-label fw-semibold">Number of Persons <span class="text-muted small">(minimum {{ min_persons }})</span></label><input type="number" id="customerPersons" class="form-control customer-modal-input" min="{{ min_persons }}" step="1" inputmode="numeric" placeholder="Minimum {{ min_persons }} persons"></div>
{% endif %}
<div class="mb-3"><label for="customerAddress" class="form-label fw-semibold">Delivery Address</label><textarea id="customerAddress" class="form-control customer-modal-input" rows="3" placeholder="Enter your complete address" autocomplete="street-address"></textarea></div>
<div id="customerDetailsError" class="alert alert-danger py-2 small" style="display:none"></div>
<div class="d-flex gap-2 mt-3"><button type="button" class="btn btn-light w-50" data-bs-dismiss="modal">Back</button><button type="button" class="btn btn-whatsapp-order w-50" onclick="confirmAndSendWhatsAppOrder()"><i class="bi bi-whatsapp me-1"></i>Send Order</button></div>
</div>
</div>
</div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
let cart={},buffetMode=null,buffetSelections={},buffetPlates=[];
const restaurantPhone="918982003335",MAX_QTY=12,MIN_BUFFET_PERSONS={{ min_persons }};
const buffetCategories={{ buffet_categories.keys()|list|tojson }};
const buffetItems={{ buffet_categories|tojson }};
const buffetAddons={{ buffet_addons|tojson }};

function addonsTotal(plate){return (plate.addons||[]).reduce((s,a)=>s+Number(a.price),0)}
function plateTotal(plate){return plate.price+plate.additional.length*50+addonsTotal(plate)}

function updateQty(id,name,price,change){
id=String(id);name=String(name);price=Number(price);change=Number(change);
if(!id||!name||!Number.isFinite(price)||!Number.isFinite(change))return;
if(!cart[id])cart[id]={id,name,price,count:0,note:""};
if(change>0&&cart[id].count>=MAX_QTY){
alert("Maximum "+MAX_QTY+" quantities allowed for "+name+".");
return;
}
cart[id].count+=change;
if(cart[id].count<=0)delete cart[id];
syncUI(id);renderCartBar();renderCartModal();
}

function syncUI(id){
const card=document.querySelector('.food-card[data-id="'+CSS.escape(id)+'"]');
if(!card)return;
const addBtn=card.querySelector('.add-btn'),qtyCtrl=card.querySelector('.qty-controls'),qtyVal=card.querySelector('.qty-val'),item=cart[id];
if(item&&item.count>0){
if(addBtn)addBtn.style.display='none';
if(qtyCtrl)qtyCtrl.style.display='flex';
if(qtyVal)qtyVal.textContent=item.count;
}else{
if(addBtn)addBtn.style.display='block';
if(qtyCtrl)qtyCtrl.style.display='none';
if(qtyVal)qtyVal.textContent='1';
}
}

function updateItemNote(id,value){if(cart[id])cart[id].note=value}

function getCartTotals(){
let totalItems=0,totalPrice=0;
Object.values(cart).forEach(item=>{totalItems+=item.count;totalPrice+=item.count*item.price});
buffetPlates.forEach(plate=>{totalItems++;totalPrice+=plateTotal(plate)});
return{totalItems,totalPrice};
}

function renderCartBar(){
const bar=document.getElementById('cartBar'),modal=document.getElementById('cartModal'),t=getCartTotals(),open=modal.classList.contains('show');
if(t.totalItems>0&&!open){
bar.style.display='flex';
document.getElementById('cartCount').textContent=t.totalItems+' ITEM'+(t.totalItems!==1?'S':'')+' ADDED';
document.getElementById('cartTotal').textContent='Total: ₹'+t.totalPrice.toFixed(0);
}else bar.style.display='none';
if(t.totalItems===0){
const o=bootstrap.Offcanvas.getInstance(modal);
if(o)o.hide();
}
}

function renderCartModal(){
const list=document.getElementById('cartItemsList');
if(!list)return;
list.innerHTML='';
let subtotal=0;
Object.values(cart).forEach(item=>{
const amount=item.count*item.price;
subtotal+=amount;
const row=document.createElement('div');row.className='cart-item-row';
const main=document.createElement('div');main.className='cart-item-main';
const left=document.createElement('div');
const name=document.createElement('div');name.className='fw-bold';name.style.color='var(--primary)';name.textContent=item.name;
const info=document.createElement('small');info.className='text-muted';info.textContent='₹'+item.price.toFixed(0)+' × '+item.count;
left.append(name,info);
const right=document.createElement('div');right.className='d-flex align-items-center gap-3';
const total=document.createElement('span');total.className='fw-bold';total.style.color='var(--primary)';total.textContent='₹'+amount.toFixed(0);
const controls=document.createElement('div');controls.className='qty-controls';controls.style.display='flex';
const minus=document.createElement('button');minus.type='button';minus.className='qty-btn';minus.dataset.cartAction='minus';minus.dataset.id=item.id;minus.textContent='−';
const qty=document.createElement('span');qty.className='qty-val';qty.textContent=item.count;
const plus=document.createElement('button');plus.type='button';plus.className='qty-btn';plus.dataset.cartAction='plus';plus.dataset.id=item.id;plus.textContent='+';
controls.append(minus,qty,plus);right.append(total,controls);main.append(left,right);
const note=document.createElement('div');note.className='cart-note';
const label=document.createElement('label');label.className='cart-note-label';label.textContent='Note for this item';
const input=document.createElement('input');input.type='text';input.className='cart-note-input';input.placeholder='e.g. Less spicy, no onion, extra butter...';input.maxLength=200;input.value=item.note||'';input.dataset.noteId=item.id;
note.append(label,input);row.append(main,note);list.appendChild(row);
});
buffetPlates.forEach((plate,index)=>{
const amount=plateTotal(plate);
subtotal+=amount;
const row=document.createElement('div');row.className='buffet-plate';
const title=document.createElement('div');title.className='d-flex justify-content-between align-items-center';
title.innerHTML='<div class="buffet-plate-title">🍽️ '+(plate.mode==="indoor"?"Indoor":"Outdoor")+' Buffet Plate '+(index+1)+'</div><div class="fw-bold" style="color:var(--primary)">₹'+amount+'</div>';
row.appendChild(title);
const base=document.createElement('div');base.className='small text-muted mt-1';base.textContent='Base: ₹'+plate.price+' + ₹'+(plate.additional.length*50)+' additional item(s) + ₹'+addonsTotal(plate)+' add-ons';row.appendChild(base);
buffetCategories.forEach(category=>{
const div=document.createElement('div');div.className='buffet-mini-category';
const selected=plate.selections[category]||[];
div.innerHTML='<b>'+category+':</b> '+(selected.length?selected.join(', '):'No selection');
row.appendChild(div);
});
const selectedSet={};
buffetCategories.forEach(category=>(plate.selections[category]||[]).forEach(name=>selectedSet[category+'|'+name]=true));
const extraBox=document.createElement('div');extraBox.className='buffet-additional';
const extraTitle=document.createElement('div');extraTitle.className='fw-bold small';extraTitle.style.color='var(--primary)';extraTitle.textContent='Add more dishes — ₹50 each';extraBox.appendChild(extraTitle);
buffetCategories.forEach(category=>{
(buffetItems[category]||[]).forEach(item=>{
const key=category+'|'+item.item_name;
if(selectedSet[key]||plate.additional.some(x=>x.category===category&&x.name===item.item_name))return;
const extra=document.createElement('div');extra.className='buffet-additional-item';
const n=document.createElement('span');n.textContent=category+' • '+item.item_name;
const btn=document.createElement('button');btn.type='button';btn.className='buffet-option-btn';btn.textContent='ADD +₹50';btn.dataset.extraPlate=plate.id;btn.dataset.extraCategory=category;btn.dataset.extraName=item.item_name;
extra.append(n,btn);extraBox.appendChild(extra);
});
});
if(extraBox.children.length>1)row.appendChild(extraBox);
if(plate.additional.length){
const added=document.createElement('div');added.className='buffet-additional mt-2';
const t=document.createElement('div');t.className='fw-bold small';t.style.color='var(--primary)';t.textContent='Additional dishes';added.appendChild(t);
plate.additional.forEach((extra,i)=>{
const line=document.createElement('div');line.className='buffet-additional-item';
const span=document.createElement('span');span.textContent=extra.category+' • '+extra.name+' — ₹50';
const remove=document.createElement('button');remove.type='button';remove.className='btn btn-sm btn-outline-danger';remove.textContent='Remove';remove.dataset.removeExtraPlate=plate.id;remove.dataset.removeExtraIndex=i;
line.append(span,remove);added.appendChild(line);
});
row.appendChild(added);
}
if(buffetAddons.length){
const addonBox=document.createElement('div');addonBox.className='buffet-additional';
const at=document.createElement('div');at.className='fw-bold small';at.style.color='var(--primary)';at.textContent='Add-ons';addonBox.appendChild(at);
buffetAddons.forEach(a=>{
const line=document.createElement('div');line.className='buffet-additional-item';
const span=document.createElement('span');
span.textContent=a.item_name+(a.description?' ('+a.description+')':'')+' — ₹'+Number(a.price).toFixed(0);
const btn=document.createElement('button');btn.type='button';btn.className='buffet-option-btn';
btn.textContent='ADD +₹'+Number(a.price).toFixed(0);btn.dataset.addonPlate=plate.id;btn.dataset.addonId=a.id;
line.append(span,btn);addonBox.appendChild(line);
});
if((plate.addons||[]).length){
const sel=document.createElement('div');sel.className='mt-2 pt-2';sel.style.borderTop='1px dashed var(--amber)';
const st=document.createElement('div');st.className='fw-bold small';st.style.color='var(--primary)';st.textContent='Added add-ons';sel.appendChild(st);
plate.addons.forEach((a,i)=>{
const line=document.createElement('div');line.className='buffet-additional-item';
const span=document.createElement('span');span.textContent=a.name+' — ₹'+Number(a.price).toFixed(0);
const rm=document.createElement('button');rm.type='button';rm.className='btn btn-sm btn-outline-danger';
rm.textContent='Remove';rm.dataset.removeAddonPlate=plate.id;rm.dataset.removeAddonIndex=i;
line.append(span,rm);sel.appendChild(line);
});
addonBox.appendChild(sel);
}
row.appendChild(addonBox);
}
const actions=document.createElement('div');actions.className='d-flex gap-2 mt-3';
const removePlate=document.createElement('button');removePlate.type='button';removePlate.className='btn btn-sm btn-light';removePlate.textContent='Remove Plate';removePlate.dataset.removePlate=plate.id;
const addSame=document.createElement('button');addSame.type='button';addSame.className='btn btn-sm btn-whatsapp-order';addSame.textContent='Add Another '+(plate.mode==="indoor"?"Indoor":"Outdoor")+' Plate';addSame.dataset.duplicatePlate=plate.id;
actions.append(removePlate,addSame);row.appendChild(actions);list.appendChild(row);
});
const gst=subtotal*5/105;
document.getElementById('billSubtotal').textContent='₹'+subtotal.toFixed(0);
document.getElementById('billTax').textContent='₹'+gst.toFixed(0);
document.getElementById('billGrandTotal').textContent='₹'+subtotal.toFixed(0);
}

function clearCart(){
Object.keys(cart).forEach(id=>{delete cart[id];syncUI(id)});
buffetPlates=[];renderCartModal();renderCartBar();
}

function selectBuffetMode(mode){
buffetMode=mode;buffetSelections={};
document.getElementById('buffetBuilder').style.display='block';
document.getElementById('selectedBuffetTitle').textContent=mode==="indoor"?"🏠 Indoor Buffet":"🌳 Outdoor Buffet";
document.getElementById('selectedBuffetDescription').textContent=mode==="indoor"?"Buffet at Vrindavan Dhaba":"Buffet at customer's location";
document.getElementById('selectedBuffetPrice').textContent='₹'+(mode==="indoor"?500:550);
document.querySelectorAll('[data-buffet-select]').forEach(btn=>{btn.classList.remove('selected');btn.textContent='SELECT'});
document.getElementById('buffetValidation').textContent='';
window.scrollTo({top:document.getElementById('buffetBuilder').offsetTop-20,behavior:'smooth'});
}

function addBuffetSelection(category,name){
if(!buffetSelections[category])buffetSelections[category]=[];
if(category==="Main Course"){
buffetSelections[category].includes(name)?buffetSelections[category]=buffetSelections[category].filter(x=>x!==name):buffetSelections[category].push(name);
}else if(category==="Breads"){
if(buffetSelections[category].includes(name))buffetSelections[category]=buffetSelections[category].filter(x=>x!==name);
else{
if(buffetSelections[category].length>=2){
document.getElementById('buffetValidation').textContent='You can select maximum 2 breads per plate.';
document.getElementById('buffetValidation').style.color='#b42318';
return;
}
buffetSelections[category].push(name);
}
}else buffetSelections[category]=[name];
updateBuffetButtons(category);
}

function updateBuffetButtons(category){
document.querySelectorAll('[data-buffet-select][data-category="'+CSS.escape(category)+'"]').forEach(btn=>{
const selected=(buffetSelections[category]||[]).includes(btn.dataset.name);
btn.classList.toggle('selected',selected);btn.textContent=selected?'SELECTED':'SELECT';
});
}

function addBuffetPlate(){
if(!buffetMode){alert('Please select Indoor or Outdoor Buffet first.');return}
const required=["Raita","Dal","Rice","Paneer","Vegetables","Desserts","Starter"];
const missing=required.filter(c=>!(buffetSelections[c]&&buffetSelections[c].length));
if(missing.length){
document.getElementById('buffetValidation').textContent='Please select one item from: '+missing.join(', ');
document.getElementById('buffetValidation').style.color='#b42318';return;
}
if(!buffetSelections.Breads||!buffetSelections.Breads.length){
document.getElementById('buffetValidation').textContent='Please select at least one bread. You can select up to 2 breads.';
document.getElementById('buffetValidation').style.color='#b42318';return;
}
buffetPlates.push({id:'buffet-'+Date.now()+'-'+Math.random().toString(36).slice(2,8),mode:buffetMode,price:buffetMode==="indoor"?500:550,selections:JSON.parse(JSON.stringify(buffetSelections)),additional:[],addons:[]});
document.getElementById('buffetValidation').textContent='Buffet plate added successfully.';
document.getElementById('buffetValidation').style.color='#2e7d32';
renderCartModal();renderCartBar();
setTimeout(()=>bootstrap.Offcanvas.getOrCreateInstance(document.getElementById('cartModal')).show(),120);
}

function duplicateBuffetPlate(id){
const source=buffetPlates.find(p=>p.id===id);if(!source)return;
const copy=JSON.parse(JSON.stringify(source));copy.id='buffet-'+Date.now()+'-'+Math.random().toString(36).slice(2,8);
buffetPlates.push(copy);renderCartModal();renderCartBar();
}

function removeBuffetPlate(id){buffetPlates=buffetPlates.filter(p=>p.id!==id);renderCartModal();renderCartBar()}

function addBuffetExtra(id,category,name){
const plate=buffetPlates.find(p=>p.id===id);if(!plate)return;
if((plate.selections[category]||[]).includes(name)||plate.additional.some(x=>x.category===category&&x.name===name))return;
plate.additional.push({category,name});renderCartModal();renderCartBar();
}

function removeBuffetExtra(id,index){
const plate=buffetPlates.find(p=>p.id===id);if(!plate)return;
plate.additional.splice(Number(index),1);renderCartModal();renderCartBar();
}

function addBuffetAddon(plateId,addonId){
const plate=buffetPlates.find(p=>p.id===plateId);
const addon=buffetAddons.find(a=>String(a.id)===String(addonId));
if(!plate||!addon)return;
if(!plate.addons)plate.addons=[];
if(plate.addons.filter(a=>a.id===addon.id).length>=MAX_QTY){alert('Maximum '+MAX_QTY+' of '+addon.item_name+' allowed.');return}
plate.addons.push({id:addon.id,name:addon.item_name,price:Number(addon.price)});
renderCartModal();renderCartBar();
}

function removeBuffetAddon(plateId,index){
const plate=buffetPlates.find(p=>p.id===plateId);if(!plate||!plate.addons)return;
plate.addons.splice(Number(index),1);renderCartModal();renderCartBar();
}

function startOrderProcess(){
if(!Object.keys(cart).length&&!buffetPlates.length){alert('Please add at least one item to your order.');return}
const modal=bootstrap.Offcanvas.getInstance(document.getElementById('cartModal'));
if(modal)modal.hide();
setTimeout(()=>{
const isBuffet={{ "true" if order_type=="buffet" else "false" }},isDinein={{ "true" if order_type=="dinein" else "false" }};
document.getElementById('customerOrderTypeLabel').textContent=isBuffet?'🍽️ Buffet':(isDinein?'🍽️ Dine In':'🥡 Parcel');
bootstrap.Modal.getOrCreateInstance(document.getElementById('customerDetailsModal')).show();
setTimeout(()=>document.getElementById('customerName').focus(),400);
},350);
}

function showCallOrderModal(){
if(!Object.keys(cart).length&&!buffetPlates.length){alert('Please add at least one item to your order.');return}
const modal=bootstrap.Offcanvas.getInstance(document.getElementById('cartModal'));
if(modal)modal.hide();
setTimeout(()=>bootstrap.Modal.getOrCreateInstance(document.getElementById('callOrderModal')).show(),350);
}

function confirmAndSendWhatsAppOrder(){
const name=document.getElementById('customerName').value.trim(),mobile=document.getElementById('customerMobile').value.trim(),address=document.getElementById('customerAddress').value.trim(),error=document.getElementById('customerDetailsError');
error.style.display='none';error.textContent='';
if(!name){error.textContent='Please enter your name.';error.style.display='block';document.getElementById('customerName').focus();return}
if(!/^[0-9]{10}$/.test(mobile)){error.textContent='Please enter a valid 10-digit mobile number.';error.style.display='block';document.getElementById('customerMobile').focus();return}
const isBuffetOrder={{ "true" if order_type=="buffet" else "false" }};
let persons=null;
if(isBuffetOrder){
const personsInput=document.getElementById('customerPersons');
persons=parseInt(personsInput.value,10);
if(!Number.isInteger(persons)||persons<MIN_BUFFET_PERSONS){error.textContent='Buffet booking requires a minimum of '+MIN_BUFFET_PERSONS+' persons.';error.style.display='block';personsInput.focus();return}
}
if(!address){error.textContent='Please enter your delivery address.';error.style.display='block';document.getElementById('customerAddress').focus();return}
sendWhatsAppOrder(name,mobile,address,persons);
}

function sendWhatsAppOrder(name,mobile,address,persons){
let message='🛕 *VRINDAVAN DHABA*\\n✨ *PURE VEG • ORDER DETAILS*\\n------------------------\\n\\n';
const isBuffet={{ "true" if order_type=="buffet" else "false" }},isDinein={{ "true" if order_type=="dinein" else "false" }};
message+=isBuffet?'🍽️ Order Mode: Buffet\\n':(isDinein?'🍽️ Order Mode: Dine In\\n':'🥡 Order Mode: Parcel\\n');
message+='👤 '+name+' | 📱 '+mobile+'\\n';
if(isBuffet&&persons)message+='👥 Number of Persons: '+persons+'\\n';
message+='📍 Address: '+address+'\\n';
const now=new Date();
message+='🕐 '+now.toLocaleDateString('en-IN',{day:'2-digit',month:'2-digit',year:'numeric'})+' '+now.toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit',hour12:true})+'\\n\\n';
message+='---------------------------------\\n           *ORDER ITEMS*\\n---------------------------------\\n\\n';
let subtotal=0;
Object.values(cart).forEach(item=>{
const qty=Number(item.count),price=Number(item.price),amount=qty*price;subtotal+=amount;
let itemName=String(item.name).replace(/\\s+/g,' ').trim();
if(item.note&&item.note.trim())itemName+=' ('+String(item.note).replace(/\\s+/g,' ').trim()+')';
message+='* '+itemName+' x '+qty+' = ₹'+amount.toFixed(0)+'\\n';
});
buffetPlates.forEach((plate,index)=>{
const amount=plateTotal(plate);subtotal+=amount;
message+='\\n*BUFFET PLATE '+(index+1)+' — '+(plate.mode==="indoor"?"INDOOR":"OUTDOOR")+'*\\nBase Price: ₹'+plate.price+'\\n';
buffetCategories.forEach(category=>{const selected=plate.selections[category]||[];if(selected.length)message+='• '+category+': '+selected.join(', ')+'\\n'});
if(plate.additional.length){
message+='Additional Items (+₹50 each):\\n';
plate.additional.forEach(extra=>message+='• '+extra.category+': '+extra.name+' = ₹50\\n');
}
if((plate.addons||[]).length){
message+='Add-ons:\\n';
plate.addons.forEach(a=>message+='• '+a.name+' = ₹'+Number(a.price).toFixed(0)+'\\n');
}
message+='Buffet Plate Total: ₹'+amount.toFixed(0)+'\\n';
});
const gst=subtotal*5/105;
message+='\\n---------------------------------\\nSubtotal: ₹'+subtotal.toFixed(0)+'\\nTaxes & Charges already included (5%): ₹'+gst.toFixed(0)+'\\n*GRAND TOTAL: ₹'+subtotal.toFixed(0)+'*\\n---------------------------------\\n\\n🙏 Thank you for ordering!\\n📞 Call 8982003335 to confirm\\nOrder is NOT placed until confirmed.';
window.open('https://wa.me/'+restaurantPhone+'?text='+encodeURIComponent(message),'_blank');
const modal=bootstrap.Modal.getInstance(document.getElementById('customerDetailsModal'));
if(modal)modal.hide();
}

function filterMenu(){
const input=document.getElementById('searchInput');if(!input)return;
const query=input.value.toLowerCase().trim(),groups=document.querySelectorAll('#menuAccordion .category-group');
let totalVisible=0;
groups.forEach(group=>{
const cards=group.querySelectorAll('.food-card');let visible=0;
cards.forEach(card=>{
const show=(card.dataset.name||'').toLowerCase().includes(query);
card.style.display=show?'flex':'none';
if(show){visible++;totalVisible++}
});
group.style.display=visible?'block':'none';
const collapse=group.querySelector('.accordion-collapse'),button=group.querySelector('.accordion-button');
if(query&&visible){new bootstrap.Collapse(collapse,{show:true});button.classList.remove('collapsed')}
});
document.getElementById('noResults').style.display=totalVisible?'none':'block';
}

function setActiveChip(el){
document.querySelectorAll('.cat-chip').forEach(x=>x.classList.remove('active'));el.classList.add('active');
}

document.addEventListener('click',e=>{
const buffet=e.target.closest('[data-buffet-select]');
if(buffet){e.preventDefault();addBuffetSelection(buffet.dataset.category,buffet.dataset.name);return}
const extra=e.target.closest('[data-extra-plate]');
if(extra){addBuffetExtra(extra.dataset.extraPlate,extra.dataset.extraCategory,extra.dataset.extraName);return}
const removeExtra=e.target.closest('[data-remove-extra-plate]');
if(removeExtra){removeBuffetExtra(removeExtra.dataset.removeExtraPlate,removeExtra.dataset.removeExtraIndex);return}
const addon=e.target.closest('[data-addon-plate]');
if(addon){addBuffetAddon(addon.dataset.addonPlate,addon.dataset.addonId);return}
const removeAddon=e.target.closest('[data-remove-addon-plate]');
if(removeAddon){removeBuffetAddon(removeAddon.dataset.removeAddonPlate,removeAddon.dataset.removeAddonIndex);return}
const removePlate=e.target.closest('[data-remove-plate]');
if(removePlate){removeBuffetPlate(removePlate.dataset.removePlate);return}
const duplicate=e.target.closest('[data-duplicate-plate]');
if(duplicate){duplicateBuffetPlate(duplicate.dataset.duplicatePlate);return}
const button=e.target.closest('[data-action],[data-cart-action]');
if(!button)return;
e.preventDefault();e.stopPropagation();
if(button.dataset.action){
const id=button.dataset.id,name=button.dataset.name,price=Number(button.dataset.price);
if(!id||!name||!Number.isFinite(price))return;
updateQty(id,name,price,button.dataset.action==='minus'?-1:1);
return;
}
if(button.dataset.cartAction){
const id=button.dataset.id;if(!cart[id])return;
updateQty(id,cart[id].name,cart[id].price,button.dataset.cartAction==='minus'?-1:1);
}
});

document.addEventListener('input',e=>{
if(e.target.matches('[data-note-id]'))updateItemNote(e.target.dataset.noteId,e.target.value);
});

document.addEventListener('DOMContentLoaded',()=>{
const cartModal=document.getElementById('cartModal');
if(cartModal){
cartModal.addEventListener('show.bs.offcanvas',()=>{document.getElementById('cartBar').style.display='none';renderCartModal()});
cartModal.addEventListener('hidden.bs.offcanvas',renderCartBar);
}
const mobile=document.getElementById('customerMobile');
if(mobile)mobile.addEventListener('input',function(){this.value=this.value.replace(/[^0-9]/g,'').slice(0,10)});
const personsField=document.getElementById('customerPersons');
if(personsField)personsField.addEventListener('input',function(){this.value=this.value.replace(/[^0-9]/g,'').slice(0,5)});

document.querySelectorAll('#menuAccordion .accordion-collapse').forEach(c=>{
c.addEventListener('show.bs.collapse',()=>{
document.querySelectorAll('#menuAccordion .accordion-collapse.show').forEach(open=>{
if(open!==c)bootstrap.Collapse.getInstance(open)?.hide();
});
});
});
});
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return redirect(url_for("menu_page",order_type="parcel"))

@app.route("/<order_type>")
def menu_page(order_type):
    if order_type not in ["dinein","parcel","buffet"]: order_type="parcel"
    categories={}
    buffet_categories={}
    buffet_addons=[]
    if order_type=="buffet":
        buffet_categories=build_buffet_menu()
        buffet_addons=build_buffet_addons()
    else:
        categories=build_menu(order_type)
    titles={"dinein":"Dine In Menu","parcel":"Takeaway / Parcel Menu","buffet":"Buffet Menu"}
    return render_template_string(MENU_TEMPLATE,categories=categories,buffet_categories=buffet_categories,
        buffet_addons=buffet_addons,min_persons=BUFFET_MIN_PERSONS,order_type=order_type,title=titles.get(order_type,"Menu"))

if __name__=="__main__":
    app.run(host="0.0.0.0",port=9991,debug=True)