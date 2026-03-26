import asyncio
import flet as ft
from typing import Any, Dict, List, Optional

import mysql.connector
from flet.fastapi import app as flet_fastapi_app


# Database config (ถ้าเชื่อมไม่ได้จะแสดงเลขจำลอง)
DB_HOST = "192.168.100.85"
DB_NAME = "Contract Management System"
DB_USER = "root"
DB_PASSWORD = "P@ssword"

def main(page: ft.Page):
    page.title = "Contract Dashboard"
    page.window_width = 420
    page.window_height = 800
    page.bgcolor = ft.Colors.GREY_50
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT

    # ====== Data (fallback to screenshot) ======
    # contracts by status
    status_counts = {
        "Active": 4,
        "Approved": 6,
        "Expired": 3,
        "Signed": 2,
        "Pending": 0,
        "Terminated": 0,
    }

    # pending cards
    pending_counts = {
        "Approval Pending": 13,
        "Negotiation Pending": 75,
        "Sign Pending": 1,
    }

    # Activities = contract documents (count)
    activity_count_total = 0

    # Lists for other tabs (empty fallback)
    contracts = []
    vendors = []
    contract_documents = []

    # ====== Fetch counts from Database ======
    # Fallback values remain if queries don't match your schema.
    try:
        # Reset counters before applying DB results
        status_counts = {
            "Active": 0,
            "Approved": 0,
            "Expired": 0,
            "Signed": 0,
            "Pending": 0,
            "Terminated": 0,
        }
        pending_counts = {
            "Approval Pending": 0,
            "Negotiation Pending": 0,
            "Sign Pending": 0,
        }

        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            connection_timeout=5,
        )
        cursor = conn.cursor(dictionary=True)

        # Contracts by status (used by the top cards)
        cursor.execute("SELECT status, COUNT(*) as count FROM contracts GROUP BY status")
        for row in cursor.fetchall() or []:
            st = str(row.get("status") or "").strip()
            if not st:
                continue
            status_counts[st] = int(row.get("count") or 0)

        # ====== Fetch full lists for each table ======
        # contracts
        cursor.execute(
            """
            SELECT
                c.contract_id,
                c.contract_number,
                c.title,
                c.status,
                c.start_date,
                c.renewal_type,
                v.vendor_name
            FROM contracts c
            LEFT JOIN vendors v ON v.vendor_id = c.vendor_id
            ORDER BY c.contract_id DESC
            LIMIT 20
            """
        )
        contracts = cursor.fetchall() or []

        # vendors
        cursor.execute(
            """
            SELECT
                vendor_id,
                vendor_name,
                contact_person,
                email,
                phone
            FROM vendors
            ORDER BY vendor_id DESC
            LIMIT 50
            """
        )
        vendors = cursor.fetchall() or []

        # contract_documents (activities)
        cursor.execute(
            """
            SELECT
                doc_id,
                contract_id,
                file_path,
                file_type,
                uploaded_at
            FROM contract_documents
            ORDER BY uploaded_at DESC
            LIMIT 30
            """
        )
        contract_documents = cursor.fetchall() or []

        # Total activity count (for header button)
        try:
            cursor.execute("SELECT COUNT(*) as count FROM contract_documents")
            row = cursor.fetchone() or {}
            activity_count_total = int(row.get("count") or 0)
        except Exception:
            activity_count_total = len(contract_documents or [])

        # Pending cards: split by renewal_type (best-effort)
        # Your screenshot uses 3 pending categories, but the DB schema only has
        # `contracts.status` + `contracts.renewal_type`. So we split Pending by renewal_type.
        computed_pending = {
            "Approval Pending": 0,
            "Negotiation Pending": 0,
            "Sign Pending": 0,
        }
        cursor.execute(
            "SELECT renewal_type, COUNT(*) as count FROM contracts WHERE status = %s GROUP BY renewal_type",
            ("Pending",),
        )
        for row in cursor.fetchall() or []:
            rt = str(row.get("renewal_type") or "").strip().lower()
            count = int(row.get("count") or 0)
            if "manual" in rt:
                computed_pending["Approval Pending"] += count
            elif "auto" in rt:
                computed_pending["Negotiation Pending"] += count
            else:
                computed_pending["Sign Pending"] += count

        # If there were no Pending rows in DB, keep fallback values.
        pending_counts = computed_pending

        conn.close()
    except Exception:
        # Keep fallback values.
        pass

    # ====== UI helpers ======
    status_count_texts: Dict[str, ft.Text] = {}

    def stat_card(title: str, count: int, bg: str, fg: str, status_key: Optional[str] = None) -> ft.Control:
        count_text = ft.Text(str(count), size=28, color=fg, weight=ft.FontWeight.W_700)
        if status_key:
            status_count_texts[status_key] = count_text
        return ft.Container(
            bgcolor=bg,
            border_radius=14,
            padding=16,
            height=100,
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(title, size=16, color=fg, weight=ft.FontWeight.W_500),
                    count_text,
                ],
            ),
        )

    def pending_card(title: str, count: int, icon: ft.IconData, bg: str, fg: str) -> ft.Control:
        return ft.Container(
            bgcolor=bg,
            border_radius=14,
            height=215,
            padding=18,
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icon, size=46, color=fg),
                    ft.Text(str(count), size=30, weight=ft.FontWeight.W_700, color=fg),
                    ft.Text(title, size=14, color=fg, text_align=ft.TextAlign.CENTER),
                ],
            ),
        )

    def filter_text(text: str) -> ft.Control:
        # Render as plain "dropdown-like" label (to look like screenshot).
        return ft.Row(
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(text, size=14, color=ft.Colors.BLACK87, weight=ft.FontWeight.W_500),
                ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, size=16, color=ft.Colors.GREY_600),
            ],
        )

    bottom_badge = ft.Container(
        bgcolor="#FF6B6B",
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=7, vertical=3),
        content=ft.Text("99+", size=11, color=ft.Colors.WHITE, weight=ft.FontWeight.W_700),
    )

    def nav_item(
        icon: ft.IconData,
        label: str,
        on_click,
        has_badge: bool = False,
    ) -> ft.Control:
        icon_stack = ft.Stack(
            width=28,
            height=28,
            controls=[
                ft.Icon(icon, size=24, color=ft.Colors.BLUE_GREY_700),
            ],
        )
        if has_badge:
            # `ft.Positioned` is not available in your Flet version.
            # Use margin inside a Stack to approximate the top-right badge.
            icon_stack.controls.append(
                ft.Container(
                    bgcolor=bottom_badge.bgcolor,
                    border_radius=bottom_badge.border_radius,
                    padding=bottom_badge.padding,
                    content=bottom_badge.content,
                    margin=ft.margin.only(left=14, top=-6),
                )
            )

        return ft.Container(
            on_click=on_click,
            padding=ft.padding.symmetric(horizontal=6),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    icon_stack,
                    ft.Text(label, size=12, color=ft.Colors.BLUE_GREY_700),
                ],
            ),
        )

    # ====== Layout ======
    header_title = ft.Text("Overview", color=ft.Colors.BLACK87, size=20, weight=ft.FontWeight.W_700)

    # Use a plain Container header instead of AppBar to avoid
    # "Unknown control: appbar" on some web/mobile runtimes.
    header = ft.Container(
        bgcolor="#fce588",
        padding=ft.Padding(12, 12, 12, 12),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.MENU, color=ft.Colors.BLACK87),
                ft.Row(
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        header_title,
                        ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, color=ft.Colors.BLACK87),
                    ],
                ),
                ft.Container(width=24),  # spacer to balance left icon
            ],
        ),
    )

    # Top-right green card live counters (updated by background loops)
    negotiations_count_text = ft.Text(
        str(status_counts.get("Pending", 0)),
        size=28,
        color=ft.Colors.WHITE,
        weight=ft.FontWeight.W_700,
    )
    activity_count_text = ft.Text(
        str(activity_count_total),
        size=20,
        color=ft.Colors.WHITE,
        weight=ft.FontWeight.W_700,
    )

    content = ft.Container(
        padding=20,
        expand=True,
        content=ft.ListView(
            spacing=18,
            controls=[
                ft.Column(
                    spacing=10,
                    controls=[
                        ft.Text(
                            "Contracts by Status",
                            size=18,
                            weight=ft.FontWeight.W_700,
                            color=ft.Colors.BLACK87,
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                filter_text("All Users"),
                                filter_text("This Year"),
                            ],
                        ),
                        ft.Row(
                            spacing=12,
                            controls=[
                                ft.Container(content=stat_card("Draft", status_counts.get("Active", 0), "#DFF5EA", "#0B6B3B", status_key="Active"), expand=True),
                                ft.Container(content=stat_card("Approved", status_counts.get("Approved", 0), "#BEECD8", "#0B6B3B", status_key="Approved"), expand=True),
                                ft.Container(content=stat_card("Activity", status_counts.get("Pending", 0), "#6FD9B5", "#FFFFFF", status_key="Pending"), expand=True),
                            ],
                        ),
                        ft.Row(
                            spacing=12,
                            controls=[
                                ft.Container(content=stat_card("Signed", status_counts.get("Signed", 0), "#7EE5C1", "#0B6B3B", status_key="Signed"), expand=True),
                                ft.Container(
                                    bgcolor="#3ECF8C",
                                    border_radius=14,
                                    height=100,
                                    padding=12,
                                    expand=True,
                                    on_click=lambda e: go_negotiations(),
                                    content=ft.Column(
                                        spacing=2,
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                        alignment=ft.MainAxisAlignment.CENTER,
                                        controls=[
                                            ft.Text(
                                                "Negotiations",
                                                size=16,
                                                color=ft.Colors.WHITE,
                                                weight=ft.FontWeight.W_500,
                                            ),
                                            negotiations_count_text,
                                        ],
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
                ft.Divider(height=1, color=ft.Colors.GREY_300),
                ft.Column(
                    spacing=10,
                    controls=[
                        ft.Text(
                            "Pending Contracts",
                            size=18,
                            weight=ft.FontWeight.W_700,
                            color=ft.Colors.BLACK87,
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                filter_text("All Users"),
                                filter_text("Overall"),
                            ],
                        ),
                        ft.Row(
                            spacing=12,
                            controls=[
                                ft.Container(
                                    content=pending_card(
                                        "Approval\nPending",
                                        pending_counts["Approval Pending"],
                                        ft.Icons.CHECK_CIRCLE,
                                        "#E7E5FF",
                                        "#4C54C7",
                                    ),
                                    expand=True,
                                ),
                                ft.Container(
                                    content=pending_card(
                                        "Negotiatio\nn Pending",
                                        pending_counts["Negotiation Pending"],
                                        ft.Icons.CHAT_BUBBLE_OUTLINE,
                                        "#FFF2CC",
                                        "#C47A00",
                                    ),
                                    expand=True,
                                ),
                                ft.Container(
                                    content=pending_card(
                                        "Sign\nPending",
                                        pending_counts["Sign Pending"],
                                        ft.Icons.EDIT,
                                        "#CFF5EF",
                                        "#1C8F70",
                                    ),
                                    expand=True,
                                ),
                            ],
                        ),
                    ],
                ),
                ft.Container(height=8),
            ],
        ),
    )

    content_slot = ft.Container(expand=True, content=content)

    def _convert_renewal_type(value: str) -> str:
        """DB enum uses a leading space for ' Auto-Renew'."""
        v = (value or "").strip()
        if not v:
            return "Manual"
        if v.lower() in ("auto-renew", "auto renew", "auto_renew"):
            return " Auto-Renew"
        # If user selected already with space or exact enum
        if v == " Auto-Renew":
            return v
        return v

    def fetch_negotiations_from_db() -> List[Dict[str, Any]]:
        """Negotiations = contracts with status='Pending'."""
        rows: List[Dict[str, Any]] = []
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                connection_timeout=5,
            )
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT
                    c.contract_id,
                    c.contract_number,
                    c.title,
                    c.status,
                    c.renewal_type,
                    c.start_date,
                    v.vendor_name
                FROM contracts c
                LEFT JOIN vendors v ON v.vendor_id = c.vendor_id
                WHERE c.status = 'Pending'
                ORDER BY c.contract_id DESC
                LIMIT 30
                """
            )
            rows = cursor.fetchall() or []
        finally:
            try:
                conn.close()
            except Exception:
                pass
        return rows

    def _days_until_end(end_date) -> Optional[int]:
        """จำนวนวันจากวันนี้ถึง end_date (0 = หมดอายุวันนี้)."""
        if end_date is None:
            return None
        from datetime import date as dt_date
        from datetime import datetime as dt_datetime

        try:
            if isinstance(end_date, dt_datetime):
                ed = end_date.date()
            elif isinstance(end_date, dt_date):
                ed = end_date
            else:
                ed = dt_date.fromisoformat(str(end_date)[:10])
            return (ed - dt_date.today()).days
        except Exception:
            return None

    def fetch_expiring_contracts_from_db(days_ahead: int = 30) -> List[Dict[str, Any]]:
        """
        เฉพาะสัญญาที่ใกล้หมดอายุ / หมดอายุภายใน N วัน (อ้างอิง contracts.end_date)
        ช่วง: วันนี้ ถึง วันนี้+N วัน — เรียง end_date จากวันที่ใกล้หมดอายุที่สุดก่อน
        """
        rows: List[Dict[str, Any]] = []
        conn = None
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                connection_timeout=5,
            )
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT
                    c.contract_id,
                    c.contract_number,
                    c.title,
                    c.end_date,
                    c.status,
                    v.vendor_name
                FROM contracts c
                LEFT JOIN vendors v ON v.vendor_id = c.vendor_id
                WHERE c.end_date IS NOT NULL
                  AND c.end_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL %s DAY)
                ORDER BY c.end_date ASC, c.contract_id ASC
                LIMIT 50
                """,
                (days_ahead,),
            )
            rows = cursor.fetchall() or []
        except Exception:
            pass
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
        return rows

    def render_negotiations_view() -> ft.Control:
        items = fetch_negotiations_from_db()
        cards: List[ft.Control] = []
        for c in items:
            cards.append(
                ft.Container(
                    bgcolor=ft.Colors.WHITE,
                    border_radius=18,
                    padding=14,
                    content=ft.Column(
                        spacing=6,
                        tight=True,
                        controls=[
                            ft.Text(
                                f"{c.get('contract_number') or ''} - {c.get('title') or ''}",
                                size=14,
                                weight=ft.FontWeight.W_700,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                f"Renewal: {c.get('renewal_type') or '-'}   |   Vendor: {c.get('vendor_name') or '-'}",
                                size=12,
                                color=ft.Colors.GREY_700,
                            ),
                            ft.Text(
                                f"Start date: {c.get('start_date') or '-'}",
                                size=12,
                                color=ft.Colors.GREY_700,
                            ),
                        ],
                    ),
                )
            )

        return ft.Container(
            padding=20,
            expand=True,
            content=ft.ListView(
                spacing=14,
                controls=[
                    ft.Text("Negotiations", size=18, weight=ft.FontWeight.W_700, color=ft.Colors.BLACK87),
                    *(cards if cards else [ft.Text("No pending negotiations", color=ft.Colors.GREY_600)]),
                    ft.Container(height=8),
                ],
            ),
        )

    negotiations_auto_refresh_enabled = False
    negotiations_loop_running = False

    # Live counters for the top-right green card (Overview screen)
    counts_auto_refresh_enabled = False
    counts_loop_running = False

    def fetch_top_counts_from_db():
        """Return (pending_contracts_count, contract_documents_count)."""
        pending = 0
        activity = 0
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            connection_timeout=5,
        )
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT COUNT(*) as c FROM contracts WHERE status = 'Pending'")
            pending_row = cursor.fetchone() or {"c": 0}
            pending = int(pending_row.get("c") or 0)

            cursor.execute("SELECT COUNT(*) as c FROM contract_documents")
            activity_row = cursor.fetchone() or {"c": 0}
            activity = int(activity_row.get("c") or 0)
        finally:
            conn.close()
        return pending, activity

    async def counts_auto_refresh_loop(_):
        nonlocal counts_auto_refresh_enabled, counts_loop_running
        while counts_auto_refresh_enabled:
            try:
                pending, activity = await asyncio.to_thread(fetch_top_counts_from_db)
                negotiations_count_text.value = str(pending)
                activity_count_text.value = str(activity)
                page.update()
            except Exception:
                pass
            await asyncio.sleep(3)
        counts_loop_running = False

    async def negotiations_auto_refresh_loop(_):
        nonlocal negotiations_auto_refresh_enabled, negotiations_loop_running
        while negotiations_auto_refresh_enabled:
            try:
                content_slot.content = render_negotiations_view()
                page.update()
            except Exception:
                # Ignore refresh errors; next loop will retry.
                pass
            await asyncio.sleep(3)
        negotiations_loop_running = False

    def go_negotiations(e=None):
        nonlocal negotiations_auto_refresh_enabled, negotiations_loop_running
        negotiations_auto_refresh_enabled = True
        header_title.value = "Negotiations"
        content_slot.content = render_negotiations_view()
        page.update()

        nonlocal counts_auto_refresh_enabled
        counts_auto_refresh_enabled = False

        # Start auto refresh loop once when entering negotiations.
        if not negotiations_loop_running:
            negotiations_loop_running = True
            page.run_task(negotiations_auto_refresh_loop, None)

    def render_create_contract_view() -> ft.Control:
        import os

        # Build lists for vendors dropdown
        vendor_options = []
        for v in vendors:
            vendor_id = v.get("vendor_id")
            vendor_name = v.get("vendor_name") or f"Vendor {vendor_id}"
            vendor_options.append(ft.dropdown.Option(key=str(vendor_id), text=vendor_name))

        contract_number = ft.TextField(label="contract_number", width=320)
        title = ft.TextField(label="title", width=320)
        description = ft.TextField(label="description", width=320, multiline=True, min_lines=3, max_lines=5)
        start_date = ft.TextField(label="start_date (YYYY-MM-DD)", width=320)
        end_date = ft.TextField(label="end_date (YYYY-MM-DD)", width=320)

        status_hint = ft.Text("Draft = status='Active', Save = status='Pending' (DB enum limited)")
        renewal_type_dd = ft.Dropdown(
            label="renewal_type",
            width=320,
            options=[
                ft.dropdown.Option(key="Manual", text="Manual"),
                ft.dropdown.Option(key="Auto-Renew", text="Auto-Renew"),
            ],
        )
        vendor_dd = ft.Dropdown(
            label="vendor_id",
            width=320,
            options=vendor_options,
        )

        selected_image = {"path": None, "bytes": None, "file_type": None, "name": None}
        image_label = ft.Text("No image selected", size=12, color=ft.Colors.GREY_600)

        error_text = ft.Text("", color=ft.Colors.RED_400, size=12)

        # FilePicker as Service (not overlay control) for web/mobile in-page picking.
        image_picker = None
        if hasattr(page, "services"):
            image_picker = next((s for s in page.services if isinstance(s, ft.FilePicker)), None)
            if image_picker is None:
                image_picker = ft.FilePicker()
                page.services.append(image_picker)

        def _pick_path() -> str:
            from tkinter import Tk, filedialog

            root = Tk()
            root.withdraw()
            root.update()
            try:
                picked = filedialog.askopenfilename(
                    title="Select image",
                    filetypes=[
                        ("Images", "*.jpg *.jpeg *.png *.webp"),
                        ("All files", "*.*"),
                    ],
                )
                return picked or ""
            finally:
                root.destroy()

        def _apply_selected_path(path_value: str):
            path_value = (path_value or "").strip()
            if not path_value:
                selected_image["path"] = None
                selected_image["bytes"] = None
                selected_image["file_type"] = None
                selected_image["name"] = None
                image_label.value = "No image selected"
                return
            ext = os.path.splitext(path_value)[1].lower().lstrip(".")
            selected_image["path"] = path_value
            selected_image["bytes"] = None
            selected_image["file_type"] = ext
            selected_image["name"] = os.path.basename(path_value)
            image_label.value = f"Selected: {selected_image['name']}"

        async def pick_image_click(e):
            # Prefer FilePicker service whenever available.
            # In some Flet runtimes, `page.web` may be False even when opened from phone browser.
            # Using service availability is more reliable and allows mobile-native picker UI.
            if image_picker is not None:
                try:
                    files = None
                    try:
                        files = await image_picker.pick_files(
                            dialog_title="Select image",
                            allowed_extensions=["jpg", "jpeg", "png", "webp"],
                            allow_multiple=False,
                            with_data=True,
                        )
                    except TypeError:
                        files = await image_picker.pick_files(
                            dialog_title="Select image",
                            allowed_extensions=["jpg", "jpeg", "png", "webp"],
                            allow_multiple=False,
                        )

                    if files:
                        first = files[0]
                        picked_name = getattr(first, "name", None) or "upload_image"
                        picked_path = getattr(first, "path", None)
                        picked_bytes = getattr(first, "bytes", None)
                        ext = os.path.splitext(picked_name)[1].lower().lstrip(".")
                        selected_image["path"] = picked_path
                        selected_image["bytes"] = picked_bytes
                        selected_image["file_type"] = ext
                        selected_image["name"] = picked_name
                        image_label.value = f"Selected: {picked_name}"
                        error_text.value = ""
                    else:
                        # user cancelled picker
                        error_text.value = ""
                except Exception as ex:
                    error_text.value = f"Pick image failed: {str(ex)}"
                page.update()
                return
            try:
                picked_path = _pick_path()
                if picked_path:
                    _apply_selected_path(picked_path)
                    error_text.value = ""
                else:
                    _apply_selected_path("")
                    error_text.value = ""
            except Exception as ex:
                error_text.value = f"Pick image failed: {str(ex)}"
            page.update()

        def _insert_contract(status_value: str):
            try:
                cn = (contract_number.value or "").strip()
                t = (title.value or "").strip()
                desc = (description.value or "").strip()
                sd = (start_date.value or "").strip()
                ed = (end_date.value or "").strip()
                vendor_id_raw = vendor_dd.value
                renewal_raw = renewal_type_dd.value

                if not cn or not t or not desc or not sd or not ed or not vendor_id_raw or not renewal_raw:
                    error_text.value = "กรุณากรอกข้อมูลให้ครบ"
                    return

                # Validate date format
                from datetime import date as _date

                start_dt = _date.fromisoformat(sd)
                end_dt = _date.fromisoformat(ed)
                vendor_id = int(vendor_id_raw)
                renewal_db = _convert_renewal_type(str(renewal_raw))

                conn = mysql.connector.connect(
                    host=DB_HOST,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    database=DB_NAME,
                    connection_timeout=5,
                )
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO contracts
                        (contract_number, title, description, start_date, end_date, vendor_id, status, renewal_type, created_at)
                    VALUES
                        (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (cn, t, desc, start_dt, end_dt, vendor_id, status_value, renewal_db),
                )
                conn.commit()

                contract_id = cursor.lastrowid

                # Upload selected image to the FastAPI so it can be stored in contract_documents.
                # This ensures `file_type` is set by the API based on the uploaded file name.
                upload_failed = False
                upload_error = ""
                if selected_image.get("path") or selected_image.get("bytes"):
                    try:
                        import base64
                        import requests

                        api_url_env = os.environ.get("API_URL", "http://127.0.0.1:3500")
                        api_urls = [
                            api_url_env,
                            "http://127.0.0.1:3500",
                            "http://localhost:3500",
                            "http://192.168.100.85:3500",
                        ]
                        # De-duplicate while preserving order
                        api_urls = [u for i, u in enumerate(api_urls) if u and u not in api_urls[:i]]

                        filename = selected_image.get("name") or "upload_image"
                        image_path = selected_image.get("path")
                        image_bytes = selected_image.get("bytes")

                        if image_bytes is not None:
                            if isinstance(image_bytes, (bytes, bytearray)):
                                file_bytes = bytes(image_bytes)
                            elif isinstance(image_bytes, str):
                                # Some runtimes may return base64 string.
                                file_bytes = base64.b64decode(image_bytes)
                            else:
                                file_bytes = bytes(image_bytes)
                        else:
                            # If file does not exist on local machine (e.g. uploaded on phone
                            # via API temp upload), attach existing server file path directly.
                            if image_path and not os.path.exists(image_path):
                                attached = False
                                attach_err = None
                                for base in api_urls:
                                    try:
                                        resp = requests.post(
                                            f"{base}/contract-documents/attach-existing",
                                            json={
                                                "contract_id": contract_id,
                                                "file_path": image_path,
                                                "file_type": selected_image.get("file_type") or "",
                                            },
                                            timeout=20,
                                        )
                                        if resp.ok:
                                            attached = True
                                            break
                                        attach_err = RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
                                    except Exception as ex:
                                        attach_err = ex
                                if not attached:
                                    raise attach_err or RuntimeError("Attach existing image failed")
                                file_bytes = None
                            else:
                                if not image_path or not os.path.exists(image_path):
                                    raise FileNotFoundError(f"Image not found: {image_path}")
                                with open(image_path, "rb") as f:
                                    file_bytes = f.read()
                                filename = os.path.basename(image_path)

                        if file_bytes is not None:
                            last_exc = None
                            resp = None
                            for base in api_urls:
                                try:
                                    resp = requests.post(
                                        f"{base}/contract-documents/upload",
                                        data={"contract_id": contract_id},
                                        files={"file": (filename, file_bytes)},
                                        timeout=20,
                                    )
                                    if resp.ok:
                                        break
                                    last_exc = RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
                                except Exception as ex:
                                    last_exc = ex

                            if resp is None or not resp.ok:
                                raise last_exc or RuntimeError("Unknown upload error")
                    except Exception as ex:
                        upload_failed = True
                        upload_error = str(ex)

                # Refresh in-memory UI data so Draft/Contracts counts update immediately.
                # - contracts list (for Contracts tab)
                # - status_counts (for Overview cards)
                dict_cursor = conn.cursor(dictionary=True)

                dict_cursor.execute(
                    "SELECT status, COUNT(*) as count FROM contracts GROUP BY status"
                )
                latest_status_counts = {}
                for row in dict_cursor.fetchall() or []:
                    latest_status_counts[str(row.get("status") or "").strip()] = int(
                        row.get("count") or 0
                    )

                for key, count_text in status_count_texts.items():
                    status_counts[key] = latest_status_counts.get(key, 0)
                    count_text.value = str(status_counts[key])

                dict_cursor.execute(
                    """
                    SELECT
                        c.contract_id,
                        c.contract_number,
                        c.title,
                        c.status,
                        c.start_date,
                        c.renewal_type,
                        v.vendor_name
                    FROM contracts c
                    LEFT JOIN vendors v ON v.vendor_id = c.vendor_id
                    ORDER BY c.contract_id DESC
                    LIMIT 20
                    """
                )
                new_contracts = dict_cursor.fetchall() or []
                contracts.clear()
                contracts.extend(new_contracts)

                # Refresh contract documents list (Activities tab)
                dict_cursor.execute(
                    """
                    SELECT doc_id, contract_id, file_path, file_type, uploaded_at
                    FROM contract_documents
                    ORDER BY doc_id DESC
                    LIMIT 30
                    """
                )
                new_docs = dict_cursor.fetchall() or []
                contract_documents.clear()
                contract_documents.extend(new_docs)

                # Refresh live counters (top-right green cards)
                try:
                    dict_cursor.execute("SELECT COUNT(*) as c FROM contracts WHERE status = 'Pending'")
                    row = dict_cursor.fetchone() or {}
                    negotiations_count_text.value = str(row.get("c", 0))
                except Exception:
                    pass
                try:
                    dict_cursor.execute("SELECT COUNT(*) as c FROM contract_documents")
                    row = dict_cursor.fetchone() or {}
                    activity_count_text.value = str(row.get("c", len(contract_documents)))
                except Exception:
                    activity_count_text.value = str(len(contract_documents))

                conn.close()

                # Show upload error and stop navigation if user picked a file but upload failed
                if upload_failed and selected_image.get("path"):
                    error_text.value = f"Image upload failed: {upload_error}"
                    page.update()
                    return

                error_text.value = ""
                # Requirement: after click Draft/Save -> reload "Create Contract" page
                # so user sees updated UI immediately.
                # Note: reload will reset form inputs (by design).
                header_title.value = "Contracts"
                content_slot.content = render_create_contract_view()
                page.update()
            except Exception as ex:
                error_text.value = f"Insert failed: {str(ex)}"

        def _on_save(e):
            _insert_contract("Pending")

        def _on_draft(e):
            _insert_contract("Active")

        return ft.Container(
            padding=20,
            expand=True,
            content=ft.ListView(
                spacing=12,
                controls=[
                    ft.Text("Create Contract", size=18, weight=ft.FontWeight.W_700, color=ft.Colors.BLACK87),
                    status_hint,
                    contract_number,
                    title,
                    description,
                    start_date,
                    end_date,
                    vendor_dd,
                    renewal_type_dd,
                    ft.Row(
                        spacing=10,
                        controls=[
                            ft.ElevatedButton(
                                "เลือกรูป",
                                icon=ft.Icons.IMAGE,
                                bgcolor=ft.Colors.GREY_300,
                                color=ft.Colors.BLACK87,
                                on_click=pick_image_click,
                            ),
                            ft.Container(
                                expand=True,
                                content=image_label,
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=10,
                        controls=[
                            ft.ElevatedButton(
                                "ร่าง",
                                bgcolor=ft.Colors.GREY_300,
                                color=ft.Colors.BLACK87,
                                on_click=_on_draft,
                            ),
                            ft.ElevatedButton(
                                "บันทึก",
                                bgcolor=ft.Colors.GREEN_400,
                                color=ft.Colors.WHITE,
                                on_click=_on_save,
                            ),
                        ],
                    ),
                    error_text,
                ],
            ),
        )


    def render_contracts_view() -> ft.Control:
        contract_cards = []
        for c in contracts[:20]:
            contract_cards.append(
                ft.Container(
                    bgcolor=ft.Colors.WHITE,
                    border_radius=18,
                    padding=14,
                    content=ft.Column(
                        spacing=6,
                        tight=True,
                        controls=[
                            ft.Text(
                                f"{c.get('contract_number') or ''} - {c.get('title') or ''}",
                                size=14,
                                weight=ft.FontWeight.W_700,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                f"Status: {c.get('status') or '-'}   |   Renewal: {(c.get('renewal_type') or '-')}",
                                size=12,
                                color=ft.Colors.GREY_700,
                            ),
                            ft.Text(
                                f"Vendor: {c.get('vendor_name') or '-'}",
                                size=12,
                                color=ft.Colors.GREY_700,
                            ),
                        ],
                    ),
                )
            )

        vendor_tiles = []
        for v in vendors[:50]:
            vendor_tiles.append(
                ft.Container(
                    bgcolor=ft.Colors.GREY_50,
                    border_radius=14,
                    padding=12,
                    content=ft.Column(
                        spacing=4,
                        tight=True,
                        controls=[
                            ft.Text(
                                v.get("vendor_name") or "-",
                                size=13,
                                weight=ft.FontWeight.W_700,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                f"{v.get('contact_person') or ''}",
                                size=12,
                                color=ft.Colors.GREY_700,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                f"{v.get('email') or ''}",
                                size=12,
                                color=ft.Colors.GREY_700,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                    ),
                )
            )

        return ft.Container(
            padding=20,
            expand=True,
            content=ft.ListView(
                spacing=14,
                controls=[
                    ft.Text("Contracts", size=18, weight=ft.FontWeight.W_700, color=ft.Colors.BLACK87),
                    ft.Container(height=6),
                    ft.ElevatedButton(
                        "สร้าง contracts",
                        bgcolor="#3ECF8C",
                        color=ft.Colors.WHITE,
                        icon=ft.Icons.ADD,
                        on_click=lambda e: (setattr(content_slot, "content", render_create_contract_view()), page.update()),
                    ),
                    ft.Container(height=10),
                    *(contract_cards if contract_cards else [ft.Text("No contracts data", color=ft.Colors.GREY_600)]),
                    ft.ExpansionTile(
                        title=ft.Text("Vendors", weight=ft.FontWeight.W_700),
                        controls=[
                            ft.Column(
                                spacing=10,
                                controls=vendor_tiles if vendor_tiles else [ft.Text("No vendors data", color=ft.Colors.GREY_600)],
                            )
                        ],
                    ),
                    ft.Container(height=8),
                ],
            ),
        )

    def render_activities_view() -> ft.Control:
        doc_cards = []
        for d in contract_documents[:30]:
            doc_cards.append(
                ft.Container(
                    bgcolor=ft.Colors.WHITE,
                    border_radius=18,
                    padding=14,
                    content=ft.Column(
                        spacing=6,
                        tight=True,
                        controls=[
                            ft.Text(
                                f"Doc #{d.get('doc_id') or '-'}  |  Contract #{d.get('contract_id') or '-'}",
                                size=13,
                                weight=ft.FontWeight.W_700,
                            ),
                            ft.Text(
                                f"Type: {(d.get('file_type') or '-')}",
                                size=12,
                                color=ft.Colors.GREY_700,
                            ),
                            ft.Text(
                                f"Path: {(d.get('file_path') or '-')}",
                                size=12,
                                color=ft.Colors.GREY_700,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                    ),
                )
            )

        return ft.Container(
            padding=20,
            expand=True,
            content=ft.ListView(
                spacing=14,
                controls=[
                    ft.Text("Activities (Contract Documents)", size=18, weight=ft.FontWeight.W_700, color=ft.Colors.BLACK87),
                    *(doc_cards if doc_cards else [ft.Text("No contract documents data", color=ft.Colors.GREY_600)]),
                    ft.Container(height=8),
                ],
            ),
        )

    def render_notifications_view() -> ft.Control:
        expiring = fetch_expiring_contracts_from_db(days_ahead=30)
        notif_cards: List[ft.Control] = []
        for c in expiring:
            days_left = _days_until_end(c.get("end_date"))
            days_txt = f"{days_left} วัน" if days_left is not None else "-"
            urgency = ft.Colors.GREY_700
            if days_left is not None and days_left <= 7:
                urgency = ft.Colors.RED_400
            elif days_left is not None and days_left <= 14:
                urgency = ft.Colors.ORANGE_700

            notif_cards.append(
                ft.Container(
                    bgcolor=ft.Colors.WHITE,
                    border_radius=18,
                    padding=14,
                    content=ft.Column(
                        spacing=6,
                        tight=True,
                        controls=[
                            ft.Text(
                                f"ใกล้หมดสัญญา · {c.get('contract_number') or ''} - {c.get('title') or ''}",
                                size=13,
                                weight=ft.FontWeight.W_700,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                f"หมดอายุ: {c.get('end_date') or '-'}  (เหลือ {days_txt})",
                                size=12,
                                color=urgency,
                                weight=ft.FontWeight.W_700,
                            ),
                            ft.Text(
                                f"สถานะ: {c.get('status') or '-'}   |   Vendor: {c.get('vendor_name') or '-'}",
                                size=12,
                                color=ft.Colors.GREY_700,
                            ),
                        ],
                    ),
                )
            )

        return ft.Container(
            padding=20,
            expand=True,
            content=ft.ListView(
                spacing=14,
                controls=[
                    ft.Text("Notifications", size=18, weight=ft.FontWeight.W_700, color=ft.Colors.BLACK87),
                    ft.Text(
                        "เฉพาะสัญญาที่ใกล้หมดอายุ / หมดอายุภายใน 30 วัน — เรียงตาม end_date (วันที่ใกล้หมดอายุสุดก่อน)",
                        size=12,
                        color=ft.Colors.GREY_600,
                    ),
                    *(notif_cards if notif_cards else [ft.Text("ไม่มีสัญญาใกล้หมดอายุในช่วงนี้", color=ft.Colors.GREY_600)]),
                    ft.Container(height=8),
                ],
            ),
        )

    def go_dashboard(e=None):
        nonlocal negotiations_auto_refresh_enabled, counts_auto_refresh_enabled, counts_loop_running
        negotiations_auto_refresh_enabled = False
        counts_auto_refresh_enabled = True
        header_title.value = "Overview"
        content_slot.content = content
        page.update()

        if not counts_loop_running:
            counts_loop_running = True
            page.run_task(counts_auto_refresh_loop, None)

    def go_contracts(e=None):
        nonlocal negotiations_auto_refresh_enabled, counts_auto_refresh_enabled
        negotiations_auto_refresh_enabled = False
        counts_auto_refresh_enabled = False
        header_title.value = "Contracts"
        content_slot.content = render_contracts_view()
        page.update()

    def go_activities(e=None):
        nonlocal negotiations_auto_refresh_enabled, counts_auto_refresh_enabled
        negotiations_auto_refresh_enabled = False
        counts_auto_refresh_enabled = False
        header_title.value = "Activities"
        content_slot.content = render_activities_view()
        page.update()

    def go_notifications(e=None):
        nonlocal negotiations_auto_refresh_enabled, counts_auto_refresh_enabled
        negotiations_auto_refresh_enabled = False
        counts_auto_refresh_enabled = False
        header_title.value = "Notifications"
        content_slot.content = render_notifications_view()
        page.update()

    bottom_bar = ft.Container(
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        bgcolor=ft.Colors.WHITE,
        border_radius=24,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                nav_item(ft.Icons.DASHBOARD, "Dashboard", on_click=go_dashboard),
                nav_item(ft.Icons.DESCRIPTION, "Contracts", on_click=go_contracts),
                nav_item(ft.Icons.ASSIGNMENT, "Activities", on_click=go_activities),
                nav_item(ft.Icons.NOTIFICATIONS_OUTLINED, "Notifications", on_click=go_notifications),
            ],
        ),
    )

    page.add(
        ft.Column(
            expand=True,
            spacing=0,
            controls=[
                header,
                content_slot,
                bottom_bar,
            ],
        )
    )


if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.FLET_APP)

# Expose ASGI app for: `uvicorn app_mobile:app --reload`
app = flet_fastapi_app(main)