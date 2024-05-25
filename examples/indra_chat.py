import webview

webview.create_window(
    "Indrajāla Chat", "https://localhost:8080/chat/index.html", width=640, height=640
)
webview.start()
