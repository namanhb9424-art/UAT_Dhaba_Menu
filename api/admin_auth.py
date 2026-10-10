import hmac
import os
import secrets
from functools import wraps

from flask import (
    Blueprint, abort, current_app, flash, redirect,
    render_template_string, request, session, url_for
)
from werkzeug.security import check_password_hash

admin_bp = Blueprint("admin", __name__)

LOGIN_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Admin Login | Vrindavan Dhaba</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#fdfbf7;min-height:100vh;display:grid;place-items:center;font-family:Arial,sans-serif}
.login{background:white;border:1px solid #ead9b2;border-radius:20px;padding:28px;width:min(92vw,420px);box-shadow:0 12px 32px #33080e18}
h1{color:#4a0e17;font-size:1.5rem;font-weight:800}
.btn-main{background:#4a0e17;color:white}
.btn-main:hover{background:#33080e;color:white}
</style>
</head>
<body>
<main class="login">
<h1>Vrindavan Dhaba</h1>
<p class="text-muted">Menu administration · Authorized access only</p>
{% for message in get_flashed_messages() %}
<div class="alert alert-warning">{{ message }}</div>
{% endfor %}
<form method="post">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<div class="mb-3">
<label class="form-label" for="username">Admin username</label>
<input class="form-control" id="username" name="username" autocomplete="username" required autofocus>
</div>
<div class="mb-3">
<label class="form-label" for="password">Password</label>
<input class="form-control" id="password" name="password" type="password" autocomplete="current-password" required>
</div>
<button class="btn btn-main w-100" type="submit">Sign in</button>
</form>
</main>
</body>
</html>
"""

def csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token

def require_csrf():
    expected = session.get("_csrf_token", "")
    supplied = request.form.get("csrf_token", "")
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        abort(400, description="Invalid security token. Refresh the page and try again.")

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin.admin_login"))
        return view(*args, **kwargs)
    return wrapped

def csrf_protected(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        require_csrf()
        return view(*args, **kwargs)
    return wrapped

@admin_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_dashboard"))

    if request.method == "POST":
        require_csrf()

        username = os.environ.get("ADMIN_USERNAME", "")
        password_hash = os.environ.get("ADMIN_PASSWORD_HASH", "")
        supplied_user = request.form.get("username", "")
        supplied_password = request.form.get("password", "")

        valid_user = bool(username) and hmac.compare_digest(
            supplied_user, username
        )
        valid_password = False

        if password_hash and supplied_password:
            try:
                valid_password = check_password_hash(
                    password_hash, supplied_password
                )
            except (ValueError, TypeError):
                current_app.logger.error("Invalid ADMIN_PASSWORD_HASH format")

        if valid_user and valid_password:
            session.clear()
            session["admin_logged_in"] = True
            session["_csrf_token"] = secrets.token_urlsafe(32)
            return redirect(url_for("admin.admin_dashboard"))

        flash("Invalid username or password.")

    return render_template_string(
        LOGIN_TEMPLATE, csrf_token=csrf_token()
    )

@admin_bp.route("/admin/logout", methods=["POST"])
@login_required
@csrf_protected
def admin_logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("admin.admin_login"))

import base64
import requests

MENU_PATH = os.getenv("GITHUB_MENU_PATH", "data/menu.json")
BUFFET_CATEGORIES = [
    "Main Course", "Raita", "Dal", "Rice", "Breads",
    "Paneer", "Vegetables", "Desserts", "Starter"
]

COLLECTIONS = {
    "menu_items": "Regular menu",
    "buffet_items": "Buffet items",
    "buffet_addons": "Buffet add-ons",
}

def github_config():
    values = {
        "token": os.getenv("GITHUB_TOKEN", ""),
        "owner": os.getenv("GITHUB_OWNER", ""),
        "repo": os.getenv("GITHUB_REPO", ""),
        "branch": os.getenv("GITHUB_BRANCH", "main"),
    }
    if not all([values["token"], values["owner"], values["repo"], values["branch"]]):
        raise RuntimeError("GitHub configuration is incomplete.")
    return values

def github_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

def read_github_menu():
    cfg = github_config()
    url = (
        f"https://api.github.com/repos/{cfg['owner']}/"
        f"{cfg['repo']}/contents/{MENU_PATH}"
    )
    response = requests.get(
        url,
        headers=github_headers(cfg["token"]),
        params={"ref": cfg["branch"]},
        timeout=15,
    )
    response.raise_for_status()
    result = response.json()

    if result.get("encoding") != "base64" or not result.get("content"):
        raise RuntimeError("GitHub did not return the expected JSON file.")

    raw = base64.b64decode(result["content"]).decode("utf-8")
    import json
    data = json.loads(raw)

    if not isinstance(data, dict):
        raise RuntimeError("The menu JSON must contain an object.")
    for key in COLLECTIONS:
        if not isinstance(data.get(key, []), list):
            raise RuntimeError(f"Invalid menu section: {key}")
        data.setdefault(key, [])

    return data, result["sha"], cfg

def save_github_menu(data, sha, cfg, message):
    import json
    url = (
        f"https://api.github.com/repos/{cfg['owner']}/"
        f"{cfg['repo']}/contents/{MENU_PATH}"
    )
    response = requests.put(
        url,
        headers=github_headers(cfg["token"]),
        json={
            "message": message,
            "content": base64.b64encode(
                json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            ).decode("ascii"),
            "sha": sha,
            "branch": cfg["branch"],
        },
        timeout=20,
    )
    if response.status_code == 409:
        raise RuntimeError(
            "The menu changed in GitHub at the same time. Reload and retry."
        )
    response.raise_for_status()

def read_form_item(collection, old=None):
    old = old or {}
    name = request.form.get("item_name", "").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()

    if not name:
        raise ValueError("Item name is required.")
    if len(name) > 150 or len(category) > 100 or len(description) > 1000:
        raise ValueError("One or more fields exceed the allowed length.")

    def price(field, default=0):
        raw = request.form.get(field, "").strip()
        if not raw:
            return default
        try:
            value = float(raw)
        except ValueError:
            raise ValueError(f"{field} must be a valid number.")
        if value < 0 or value > 1000000:
            raise ValueError(f"{field} must be between 0 and 1000000.")
        return int(value) if value.is_integer() else value

    def checked(field, default=True):
        if field not in request.form:
            return False
        return request.form.get(field) == "on"

    item = dict(old)
    item.update({
        "item_name": name,
        "description": description,
        "is_active": checked("is_active", old.get("is_active", True)),
    })

    if collection == "menu_items":
        if not category:
            raise ValueError("Category is required.")
        item.update({
            "category": category,
            "dine_in_price": price("dine_in_price"),
            "pickup_price": price("pickup_price"),
            "online_price": price("online_price"),
            "dine_in_active": checked("dine_in_active"),
            "pickup_active": checked("pickup_active"),
            "online_active": checked("online_active"),
        })
    elif collection == "buffet_items":
        if category not in BUFFET_CATEGORIES:
            raise ValueError("Choose a valid buffet category.")
        item["category"] = category
    else:
        item["price"] = price("price")
    return item

def next_id(items):
    numeric_ids = []
    for item in items:
        try:
            numeric_ids.append(int(item.get("id", 0)))
        except (ValueError, TypeError):
            pass
    return max(numeric_ids, default=0) + 1

def commit_menu_change(data, sha, cfg, message):
    save_github_menu(data, sha, cfg, message)


@admin_bp.route("/admin")
@login_required
def admin_dashboard():
    DASHBOARD_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Menu Admin | Vrindavan Dhaba</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#fdfbf7;color:#331016;font-family:Arial,sans-serif}
header{background:#4a0e17;color:white;padding:18px}
.card{border-color:#ead9b2;border-radius:14px}
.btn-main{background:#4a0e17;color:white}
.table-responsive{overflow-x:auto}
</style>
</head>
<body>
<header class="d-flex justify-content-between align-items-center">
<div><strong>Vrindavan Dhaba</strong><div class="small">Menu Admin</div></div>
<form method="post" action="{{ url_for('admin.admin_logout') }}">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<button class="btn btn-sm btn-outline-light">Log out</button>
</form>
</header>
<main class="container py-4">
{% for category, message in get_flashed_messages(with_categories=true) %}
<div class="alert alert-{{ category }}">{{ message }}</div>
{% endfor %}
<div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
<h1 class="h3">Menu management</h1>
<a class="btn btn-outline-dark" href="{{ url_for('admin.admin_dashboard') }}">Refresh</a>
</div>
<div class="row g-3 mb-4">
{% for key, label in collections.items() %}
<div class="col-12 col-md-4"><div class="card p-3">
<div class="text-muted">{{ label }}</div><div class="fs-3 fw-bold">{{ data[key]|length }}</div>
</div></div>
{% endfor %}
</div>
<div class="card p-3 mb-4">
<h2 class="h5">Add menu item</h2>
<form method="post" action="{{ url_for('admin.admin_create') }}" class="row g-3">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<div class="col-12 col-md-4">
<label class="form-label">Item type</label>
<select class="form-select" name="collection" id="collection" onchange="toggleFields()" required>
<option value="menu_items">Regular menu</option>
<option value="buffet_items">Buffet item</option>
<option value="buffet_addons">Buffet add-on</option>
</select></div>
<div class="col-12 col-md-4"><label class="form-label">Item name</label><input class="form-control" name="item_name" maxlength="150" required></div>
<div class="col-12 col-md-4" id="categoryField"><label class="form-label">Category</label>
<input class="form-control" name="category" id="categoryText">
<select class="form-select" id="categorySelect" name="category" style="display:none">
{% for category in buffet_categories %}<option>{{ category }}</option>{% endfor %}
</select></div>
<div class="col-12"><label class="form-label">Description</label><input class="form-control" name="description" maxlength="1000"></div>
<div class="col-6 col-md-4 priceField"><label class="form-label">Dine-in price</label><input class="form-control" name="dine_in_price" type="number" min="0" step="0.01" value="0"></div>
<div class="col-6 col-md-4 priceField"><label class="form-label">Parcel price</label><input class="form-control" name="pickup_price" type="number" min="0" step="0.01" value="0"></div>
<div class="col-6 col-md-4 priceField"><label class="form-label">Online price</label><input class="form-control" name="online_price" type="number" min="0" step="0.01" value="0"></div>
<div class="col-6 col-md-4" id="addonPrice" style="display:none"><label class="form-label">Add-on price</label><input class="form-control" name="price" type="number" min="0" step="0.01" value="0"></div>
<div class="col-12 d-flex flex-wrap gap-3" id="regularFlags">
{% for field, label in [('dine_in_active','Dine-in enabled'),('pickup_active','Parcel enabled'),('online_active','Online enabled')] %}
<label><input type="checkbox" name="{{ field }}" checked> {{ label }}</label>
{% endfor %}
</div>
<div class="col-12"><label><input type="checkbox" name="is_active" checked> Item is active</label></div>
<div class="col-12"><button class="btn btn-main">Add item and save to GitHub</button></div>
</form>
</div>
<div class="card p-3">
<div class="d-flex flex-wrap justify-content-between gap-2">
<h2 class="h5">Existing items</h2>
<input id="search" class="form-control" style="max-width:300px" placeholder="Search items..." oninput="filterRows()">
</div>
<div class="table-responsive mt-3"><table class="table align-middle">
<thead><tr><th>Type</th><th>Name</th><th>Category</th><th>Price</th><th>Status</th><th>Actions</th></tr></thead>
<tbody id="itemsBody">
{% for collection, items in data.items() %}
{% if collection in collections %}
{% for item in items %}
<tr data-search="{{ (item.get('item_name','') ~ ' ' ~ item.get('category','') ~ ' ' ~ collections[collection])|lower }}">
<td>{{ collections[collection] }}</td>
<td>{{ item.get('item_name','') }}</td>
<td>{{ item.get('category','—') }}</td>
<td>
{% if collection == 'menu_items' %}
Dine-in ₹{{ item.get('dine_in_price',0) }}<br>Parcel ₹{{ item.get('pickup_price',0) }}<br>Online ₹{{ item.get('online_price',0) }}
{% elif collection == 'buffet_addons' %}
₹{{ item.get('price',0) }}
{% else %}—{% endif %}
</td>
<td>{{ 'Active' if item.get('is_active', true) else 'Inactive' }}</td>
<td class="text-nowrap">
<a class="btn btn-sm btn-outline-primary" href="{{ url_for('admin.admin_edit', collection=collection, index=loop.index0) }}">Edit</a>
<form method="post" action="{{ url_for('admin.admin_delete', collection=collection, index=loop.index0) }}" class="d-inline" onsubmit="return confirm('Delete this item permanently?')">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<button class="btn btn-sm btn-outline-danger">Delete</button>
</form>
</td>
</tr>
{% endfor %}
{% endif %}
{% endfor %}
</tbody></table></div>
</div>
</main>
<script>
function toggleFields(){
const type=document.getElementById('collection').value;
const regular=type==='menu_items',buffet=type==='buffet_items',addon=type==='buffet_addons';
document.querySelectorAll('.priceField').forEach(e=>e.style.display=regular?'block':'none');
document.getElementById('addonPrice').style.display=addon?'block':'none';
document.getElementById('regularFlags').style.display=regular?'flex':'none';
document.getElementById('categoryField').style.display=addon?'none':'block';
document.getElementById('categoryText').style.display=regular?'block':'none';
document.getElementById('categorySelect').style.display=buffet?'block':'none';
document.getElementById('categoryText').disabled=!regular;
document.getElementById('categorySelect').disabled=!buffet;
}
function filterRows(){
const q=document.getElementById('search').value.toLowerCase();
document.querySelectorAll('#itemsBody tr').forEach(r=>r.style.display=r.dataset.search.includes(q)?'':'none');
}
toggleFields();
</script>
</body></html>
"""

EDIT_TEMPLATE = """
<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Edit menu item</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body style="background:#fdfbf7">
<main class="container py-4" style="max-width:760px">
<h1 class="h3">Edit {{ label }}</h1><p>{{ item.get('item_name','') }}</p>
{% for category, message in get_flashed_messages(with_categories=true) %}
<div class="alert alert-{{ category }}">{{ message }}</div>{% endfor %}
<form method="post" class="card card-body">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<div class="mb-3"><label class="form-label">Item name</label><input class="form-control" name="item_name" value="{{ item.get('item_name','') }}" required maxlength="150"></div>
{% if collection != 'buffet_addons' %}
<div class="mb-3"><label class="form-label">Category</label>
{% if collection == 'buffet_items' %}
<select class="form-select" name="category">{% for c in buffet_categories %}<option value="{{ c }}" {{ 'selected' if item.get('category')==c else '' }}>{{ c }}</option>{% endfor %}</select>
{% else %}<input class="form-control" name="category" value="{{ item.get('category','') }}" required>{% endif %}
</div>{% endif %}
<div class="mb-3"><label class="form-label">Description</label><textarea class="form-control" name="description" maxlength="1000">{{ item.get('description','') }}</textarea></div>
{% if collection == 'menu_items' %}
{% for field, label in [('dine_in_price','Dine-in price'),('pickup_price','Parcel price'),('online_price','Online price')] %}
<div class="mb-3"><label class="form-label">{{ label }}</label><input class="form-control" type="number" min="0" step="0.01" name="{{ field }}" value="{{ item.get(field,0) }}"></div>{% endfor %}
{% for field, label in [('dine_in_active','Dine-in enabled'),('pickup_active','Parcel enabled'),('online_active','Online enabled')] %}
<label class="me-3 mb-3"><input type="checkbox" name="{{ field }}" {{ 'checked' if item.get(field,true) else '' }}> {{ label }}</label>{% endfor %}
{% elif collection == 'buffet_addons' %}
<div class="mb-3"><label class="form-label">Add-on price</label><input class="form-control" type="number" min="0" step="0.01" name="price" value="{{ item.get('price',0) }}"></div>
{% endif %}
<div class="mb-3"><label><input type="checkbox" name="is_active" {{ 'checked' if item.get('is_active',true) else '' }}> Item is active</label></div>
<button class="btn btn-dark">Save changes to GitHub</button>
<a class="btn btn-outline-secondary mt-2" href="{{ url_for('admin.admin_dashboard') }}">Cancel</a>
</form></main></body></html>
"""

def get_csrf():
    return csrf_token()

@admin_bp.route("/admin", methods=["GET"])
@login_required
def admin_dashboard():
    try:
        data, _, _ = read_github_menu()
    except Exception:
        current_app.logger.exception("Could not read menu from GitHub")
        return (
            "Could not load menu from GitHub. Check the server logs and "
            "GitHub Environment Variables.",
            503,
        )
    return render_template_string(
        DASHBOARD_TEMPLATE,
        data=data,
        collections=COLLECTIONS,
        buffet_categories=BUFFET_CATEGORIES,
        csrf_token=get_csrf(),
    )

@admin_bp.route("/admin/create", methods=["POST"])
@login_required
@csrf_protected
def admin_create():
    collection = request.form.get("collection", "")
    if collection not in COLLECTIONS:
        abort(400, description="Invalid item type.")
    try:
        data, sha, cfg = read_github_menu()
        item = read_form_item(collection)
        item["id"] = next_id(data[collection])
        data[collection].append(item)
        commit_menu_change(
            data, sha, cfg, f"Add {collection[:-1]}: {item['item_name']}"
        )
        flash("Item added and committed to GitHub.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    except Exception:
        current_app.logger.exception("Menu create failed")
        flash("Could not save the item. Check server logs and GitHub settings.", "danger")
    return redirect(url_for("admin.admin_dashboard"))

@admin_bp.route("/admin/edit/<collection>/<int:index>", methods=["GET", "POST"])
@login_required
def admin_edit(collection, index):
    if collection not in COLLECTIONS:
        abort(404)
    try:
        data, sha, cfg = read_github_menu()
        items = data[collection]
        if index < 0 or index >= len(items):
            abort(404)
        item = items[index]
        if request.method == "POST":
            require_csrf()
            updated = read_form_item(collection, item)
            updated["id"] = item.get("id", next_id(items))
            items[index] = updated
            commit_menu_change(
                data, sha, cfg, f"Update {collection[:-1]}: {updated['item_name']}"
            )
            flash("Changes saved to GitHub.", "success")
            return redirect(url_for("admin.admin_dashboard"))
        return render_template_string(
            EDIT_TEMPLATE,
            collection=collection,
            label=COLLECTIONS[collection],
            item=item,
            buffet_categories=BUFFET_CATEGORIES,
            csrf_token=get_csrf(),
        )
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("admin.admin_dashboard"))
    except Exception:
        current_app.logger.exception("Menu edit failed")
        return "Could not load or save this item. Check server logs.", 503

@admin_bp.route("/admin/delete/<collection>/<int:index>", methods=["POST"])
@login_required
@csrf_protected
def admin_delete(collection, index):
    if collection not in COLLECTIONS:
        abort(404)
    try:
        data, sha, cfg = read_github_menu()
        items = data[collection]
        if index < 0 or index >= len(items):
            abort(404)
        name = items[index].get("item_name", "item")
        items.pop(index)
        commit_menu_change(data, sha, cfg, f"Delete {collection[:-1]}: {name}")
        flash("Item deleted from GitHub.", "success")
    except Exception:
        current_app.logger.exception("Menu delete failed")
        flash("Could not delete the item. Check server logs.", "danger")
    return redirect(url_for("admin.admin_dashboard"))
    return (
        "Admin authentication is working. Add the CRUD routes "
        "from Step 3 to enable menu management."
    )