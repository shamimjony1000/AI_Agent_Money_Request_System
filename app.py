import gradio as gr
from ui import create_ui

if __name__ == "__main__":
    app = create_ui()
    app.launch()