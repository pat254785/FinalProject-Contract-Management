import flet as ft
import requests
import os
import warnings

# This project uses `ft.app()` for Flet runtime start.
# Flet marks it as deprecated, but the recommended `ft.run()` is not available
# in the current Flet version, so we suppress this specific warning.
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=r"app\(\) is deprecated.*",
)

def main(page: ft.Page):
    page.title = "Login"
    page.window_width = 420
    page.window_height = 800
    page.bgcolor = ft.Colors.GREY_50
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0

    # API configuration
    # API_URL must point to where uvicorn/FastAPI is running.
    # Using server IP avoids "Cannot connect to login api" when frontend is on a different machine.
    # Default to localhost for desktop dev.
    # Override by setting environment variable: API_URL=http://<ip>:<port>
    API_URL = os.environ.get("API_URL", "http://127.0.0.1:3500")
    api_url_candidates = []
    # Put the preferred URL first.
    if API_URL:
        api_url_candidates.append(API_URL)
    # Common fallbacks.
    api_url_candidates.extend(
        [
            "http://127.0.0.1:3500",
            "http://localhost:3500",
            "http://192.168.100.85:3500",
        ]
    )
    # Deduplicate while keeping order.
    seen = set()
    api_url_candidates = [x for x in api_url_candidates if not (x in seen or seen.add(x))]

    # Loading indicator
    loading = ft.ProgressRing(visible=False)

    # Login controls
    login_error = ft.Text("", color="red")
    username_field = ft.TextField(label="Username", width=300)
    password_field = ft.TextField(
        label="Password",
        password=True,
        can_reveal_password=True,
        width=300,
    )

    def on_login(e):
        login_error.value = ""
        loading.visible = True
        page.update()

        last_conn_err = None
        tried = []
        try:
            for base in api_url_candidates:
                tried.append(base)
                try:
                    response = requests.post(
                        f"{base}/user_login",
                        json={
                            "username": username_field.value,
                            "password": password_field.value,
                        },
                        timeout=5,
                    )
                except requests.exceptions.ConnectionError as ce:
                    last_conn_err = ce
                    continue

                # Got a response; decide based on status/json.
                if response.status_code == 200 and response.json().get("success"):
                    # Switch to app page in the same Flet session.
                    page.controls.clear()
                    page.floating_action_button = None
                    import app_mobile

                    app_mobile.main(page)
                    page.update()
                    return

                if response.status_code in (401, 400):
                    login_error.value = "Invalid username or password"
                    return

                # Other response types: treat as error and stop
                login_error.value = f"Login failed ({response.status_code})"
                return

            # If we got here, we couldn't connect to any candidate.
            if last_conn_err is not None:
                login_error.value = (
                    "Cannot connect to login API. "
                    f"Tried: {', '.join(tried)}"
                )
            else:
                login_error.value = "Cannot connect to login API."

        except Exception as ex:
            login_error.value = f"Error: {str(ex)}"
        finally:
            loading.visible = False
            page.update()

    def show_login():
        page.controls.clear()
        page.floating_action_button = None

        header = ft.Container(
            bgcolor="#fce588",
            padding=ft.Padding(16, 14, 16, 14),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.LOGIN, color=ft.Colors.BLACK87),
                    ft.Text(
                        "Login",
                        color=ft.Colors.BLACK87,
                        size=20,
                        weight=ft.FontWeight.W_700,
                    ),
                ],
            ),
        )

        form_card = ft.Container(
            bgcolor=ft.Colors.WHITE,
            border_radius=24,
            padding=ft.Padding(20, 20, 20, 20),
            width=340,
            content=ft.Column(
                [
                    ft.Text("Welcome Back", size=28, weight="bold", color=ft.Colors.BLACK87),
                    ft.Text("Sign in to continue", size=15, color=ft.Colors.GREY_600),
                    ft.Divider(thickness=1, height=20),
                    username_field,
                    password_field,
                    ft.Button(
                        "Login",
                        on_click=on_login,
                        width=300,
                        bgcolor="#3ECF8C",
                        color=ft.Colors.WHITE,
                    ),
                    login_error,
                    loading,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
        )

        page.add(
            ft.Column(
                [
                    header,
                    ft.Row(
                        expand=True,
                        alignment=ft.MainAxisAlignment.CENTER,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[form_card],
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
                expand=True,
            )
        )

    # Start with login screen
    show_login()


if __name__ == "__main__":
    # Use `ft.app()` for compatibility across flet versions.
    ft.app(target=main, view=ft.AppView.FLET_APP)