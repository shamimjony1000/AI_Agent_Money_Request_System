import gradio as gr
import pandas as pd
from database import Database
from voice import VoiceHandler
from gemini import GeminiProcessor
from memory import MemoryHandler
from text_to_speech import play_text

def create_ui():
    # Initialize components
    db = Database()
    voice_handler = VoiceHandler()
    gemini_processor = GeminiProcessor()
    memory_handler = MemoryHandler()

    def validate_request(project_number, project_name, amount, reason):
        if not project_number or not project_name or not amount or not reason:
            missing_fields = []
            if not project_number: missing_fields.append("project number")
            if not project_name: missing_fields.append("project name")
            if not amount: missing_fields.append("amount")
            if not reason: missing_fields.append("reason")
            return False, f"Please provide: {', '.join(missing_fields)}"
        return True, ""

    def process_text_input(text, language):
        if not text:
            return "Please enter some text first.", None, None, None, None
        
        context = memory_handler.get_context()
        details = gemini_processor.extract_request_details(text, context)
        
        if not details:
            return "Could not extract request details. Please try again.", None, None, None, None
        
        memory_handler.add_interaction(text, details)
        partial_info = memory_handler.get_partial_info()
        
        return (
            f"Text processed! {memory_handler.get_prompt_for_missing_info()}",
            partial_info.get('project_number', ''),
            partial_info.get('project_name', ''),
            partial_info.get('amount', 0),
            partial_info.get('reason', '')
        )

    def process_voice_input(audio_path, language):
        if not audio_path:
            return "No audio detected.", None, None, None, None
        
        voice_text = voice_handler.process_audio_file(audio_path, language)
        if voice_text.startswith("Error:"):
            return voice_text, None, None, None, None
        
        context = memory_handler.get_context()
        details = gemini_processor.extract_request_details(voice_text, context)
        
        if not details:
            return "Could not extract request details. Please try again.", None, None, None, None
        
        memory_handler.add_interaction(voice_text, details)
        partial_info = memory_handler.get_partial_info()

        return (
            f"Voice processed! You said: {voice_text}\n\n{memory_handler.get_prompt_for_missing_info()}",
            partial_info.get('project_number', ''),
            partial_info.get('project_name', ''),
            partial_info.get('amount', 0),
            partial_info.get('reason', '')
        )

    def confirm_submission(project_number, project_name, amount, reason):
        is_valid, message = validate_request(project_number, project_name, amount, reason)
        if not is_valid:
            return (
                message,  # confirmation_output
                None,    # confirmation_audio
                gr.update(interactive=False),  # submit_btn
                gr.update(interactive=True),   # confirm_btn
                gr.update(interactive=True),   # project_number
                gr.update(interactive=True),   # project_name
                gr.update(interactive=True),   # amount
                gr.update(interactive=True)    # reason
            )
        
        confirmation_text = f"Sir please ensure before submit project number: {project_number}, project name: {project_name}, amount: {amount} riyals, reason for request: {reason} are ok"
        audio_path, error = play_text(confirmation_text)
        
        if error:
            return (
                error,   # confirmation_output
                None,    # confirmation_audio
                gr.update(interactive=False),  # submit_btn
                gr.update(interactive=True),   # confirm_btn
                gr.update(interactive=True),   # project_number
                gr.update(interactive=True),   # project_name
                gr.update(interactive=True),   # amount
                gr.update(interactive=True)    # reason
            )
        
        return (
            "Please confirm the details you heard.",  # confirmation_output
            audio_path,                              # confirmation_audio
            gr.update(interactive=True),             # submit_btn
            gr.update(interactive=False),            # confirm_btn
            gr.update(interactive=False),            # project_number
            gr.update(interactive=False),            # project_name
            gr.update(interactive=False),            # amount
            gr.update(interactive=False)             # reason
        )

    def submit_request(project_number, project_name, amount, reason):
        is_valid, message = validate_request(project_number, project_name, amount, reason)    

        if not is_valid:
            return message, None
        
        try:
            db.add_request(project_number, project_name, float(amount), reason)
            memory_handler.clear_memory()
            return "Request successfully added!", get_requests_df()
        except Exception as e:
            return f"Error saving request: {str(e)}", None

    def get_requests_df():
        try:
            requests = db.get_all_requests()
            if requests:
                df = pd.DataFrame(requests)
                columns = ['timestamp', 'project_number', 'project_name', 'amount', 'reason']
                df = df[columns]
                headers = df.columns.tolist()
                data = df.values.tolist()
                return {"headers": headers, "data": data}
            return {"headers": ['timestamp', 'project_number', 'project_name', 'amount', 'reason'], "data": []}
        except Exception as e:
            print(f"Error getting requests: {str(e)}")
            return {"headers": ['timestamp', 'project_number', 'project_name', 'amount', 'reason'], "data": []}

    def reset_form():
        return (
            gr.update(value=""),             # project_number
            gr.update(value=""),             # project_name
            gr.update(value=None),           # amount
            gr.update(value=""),             # reason
            gr.update(value=""),             # confirmation_output
            gr.update(value=None),           # confirmation_audio
            gr.update(interactive=False),    # submit_btn
            gr.update(interactive=True),     # confirm_btn
            gr.update(interactive=True),     # project_number
            gr.update(interactive=True),     # project_name
            gr.update(interactive=True),     # amount
            gr.update(interactive=True),     # reason
            gr.update(value=""),            # text_input
            gr.update(value=None),          # audio_input
            gr.update(value="")             # process_output
        )

    # Create UI layout
    with gr.Blocks(title="AI Agent Money Request System") as app:
        gr.Markdown("# AI Agent Money Request System")
        
        with gr.Tab("Input"):
            language = gr.Dropdown(
                choices=["English", "Arabic", "Mixed (Arabic/English)"],
                value="English",
                label="Select Language"
            )
            
            with gr.Tab("Voice Input"):
                audio_input = gr.Audio(
                    label="Voice Input",
                    type="filepath",
                    sources=["microphone"]
                )
                voice_process_btn = gr.Button("Process Voice")
            
            with gr.Tab("Text Input"):
                text_input = gr.Textbox(
                    lines=3,
                    placeholder="Enter your request here...",
                    label="Text Input"
                )
                text_process_btn = gr.Button("Process Text")
            
            process_output = gr.Textbox(label="Processing Result")
            
            with gr.Group():
                project_number = gr.Textbox(label="Project Number")
                project_name = gr.Textbox(label="Project Name")
                amount = gr.Number(label="Amount (in riyals)")
                reason = gr.Textbox(label="Reason for Request")
                
                with gr.Row():
                    confirm_btn = gr.Button("Confirm Details", variant="secondary")
                    submit_btn = gr.Button("Submit Request", variant="primary", interactive=False)
                
                confirmation_output = gr.Textbox(label="Confirmation Message")
                confirmation_audio = gr.Audio(label="Confirmation Audio", type="filepath")
            
            result_text = gr.Textbox(label="Submission Result")
        
        with gr.Tab("Existing Requests"):
            requests_table = gr.DataFrame(
                headers=["Timestamp", "Project Number", "Project Name", "Amount", "Reason"],
                label="Existing Requests"
            )
            refresh_btn = gr.Button("Refresh")
        
        # Event handlers
        text_process_btn.click(
            process_text_input,
            inputs=[text_input, language],
            outputs=[process_output, project_number, project_name, amount, reason]
        )
        
        voice_process_btn.click(
            process_voice_input,
            inputs=[audio_input, language],
            outputs=[process_output, project_number, project_name, amount, reason]
        )
        
        # Confirm button handler with proper submit button and form field state management
        confirm_btn.click(
            confirm_submission,
            inputs=[project_number, project_name, amount, reason],
            outputs=[
                confirmation_output,
                confirmation_audio,
                submit_btn,
                confirm_btn,
                project_number,
                project_name,
                amount,
                reason
            ]
        )
        
        # Submit button handler with form reset
        submit_btn.click(
            submit_request,
            inputs=[project_number, project_name, amount, reason],
            outputs=[result_text, requests_table]
        ).then(
            reset_form,
            outputs=[
                project_number,
                project_name,
                amount,
                reason,
                confirmation_output,
                confirmation_audio,
                submit_btn,
                confirm_btn,
                project_number,
                project_name,
                amount,
                reason,
                text_input,
                audio_input,
                process_output
            ]
        )
        
        refresh_btn.click(
            lambda: get_requests_df(),
            outputs=[requests_table]
        )
        
        # Initialize requests table
        requests_table.value = get_requests_df()
    
    return app
