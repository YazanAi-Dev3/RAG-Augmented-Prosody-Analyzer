import gradio as gr

from .config import TASK_OPTIONS
from .handlers import (
    analyze_and_store,
    clear_inputs,
    login_user,
    logout_user,
    refresh_history,
    register_user,
    view_history_item,
)
from .rendering import status_badge


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="Arab Poet Gradio MVP") as demo:
        user_state = gr.State({})

        gr.Markdown(
            """
            <div class="hero">
                <h1>Arab Poet Interface</h1>
            </div>
            """
        )

        global_status = gr.HTML(status_badge("بانتظار تسجيل الدخول", "muted"))
        welcome_box = gr.HTML("")

        with gr.Column(visible=True, elem_classes=["panel"]) as auth_panel:
            gr.Markdown("### تسجيل الدخول أو إنشاء حساب")
            username = gr.Textbox(label="اسم المستخدم", placeholder="مثال: ali")
            password = gr.Textbox(label="كلمة المرور", placeholder="6 أحرف على الأقل", type="password")
            with gr.Row():
                login_btn = gr.Button("تسجيل الدخول", variant="primary")
                register_btn = gr.Button("إنشاء حساب", variant="secondary")

        with gr.Column(visible=False) as app_panel:
            with gr.Row():
                logout_btn = gr.Button("تسجيل الخروج", variant="secondary")
                refresh_btn = gr.Button("تحديث السجل", variant="secondary")

            with gr.Row():
                with gr.Column(scale=5, elem_classes=["panel"]):
                    poem_text = gr.Textbox(
                        label="نص القصيدة",
                        placeholder="اكتب البيت أو القصيدة هنا...",
                        lines=10,
                        text_align="right",
                    )
                    task = gr.Radio(
                        choices=TASK_OPTIONS,
                        value="all",
                        label="نوع التحليل",
                        info="",
                    )
                    is_full_poem = gr.Checkbox(
                        value=False,
                        label="النص قصيدة كاملة متعددة الأبيات",
                    )
                    with gr.Row():
                        analyze_btn = gr.Button("ابدأ التحليل", variant="primary")
                        clear_btn = gr.Button("مسح الحقول", variant="secondary")

                with gr.Column(scale=7, elem_classes=["panel"]):
                    status_box = gr.HTML(status_badge("جاهز", "muted"))
                    summary_box = gr.HTML()

            with gr.Row():
                with gr.Column(scale=6, elem_classes=["panel"]):
                    gr.Markdown("### السجل السابق")
                    history_table = gr.Dataframe(
                        headers=["ID", "التاريخ", "المهمة", "قصيدة كاملة", "الحالة", "مقتطف"],
                        value=[],
                        interactive=False,
                        wrap=True,
                    )
                with gr.Column(scale=6, elem_classes=["panel"]):
                    gr.Markdown("### استرجاع عنصر من السجل")
                    history_choice = gr.Dropdown(choices=[], label="اختر عنصرًا من السجل")
                    load_btn = gr.Button("تحميل العنصر المحدد", variant="secondary")

        register_btn.click(
            fn=register_user,
            inputs=[username, password],
            outputs=[user_state, global_status, auth_panel, app_panel, welcome_box],
        )

        login_btn.click(
            fn=login_user,
            inputs=[username, password],
            outputs=[user_state, global_status, auth_panel, app_panel, welcome_box],
        )

        logout_btn.click(
            fn=logout_user,
            inputs=None,
            outputs=[user_state, global_status, auth_panel, app_panel, welcome_box, summary_box, history_table, history_choice],
        )

        analyze_btn.click(
            fn=analyze_and_store,
            inputs=[poem_text, task, is_full_poem, user_state],
            outputs=[summary_box, status_box, history_table, history_choice],
        )

        refresh_btn.click(
            fn=refresh_history,
            inputs=[user_state],
            outputs=[history_table, history_choice, status_box],
        )

        load_btn.click(
            fn=view_history_item,
            inputs=[history_choice, user_state],
            outputs=[poem_text, task, is_full_poem, summary_box],
        )

        clear_btn.click(
            fn=clear_inputs,
            inputs=None,
            outputs=[poem_text, task, is_full_poem, status_box, summary_box],
        )

    return demo
