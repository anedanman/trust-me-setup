import json
import os
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime

"""
   Spawn UI window. 

   Basic flow:
       Every 3hrs or upon StreamDeck button press spawn UI for questions. 

    TODO:
        Script that listens for streamdeck input + cronjob for every 3 hrs
"""

CATEGORY = ""


def formatted_time():
    return "{:%Y-%m-%d$%H-%M-%S-%f}".format(datetime.now())


@dataclass
class Question:
    """Class representing a question and its parameters"""

    text: str
    text_slider_min: str
    text_slider_max: str
    scale_size: int


class Poll:
    def __init__(self, root, questions):
        self.root = root
        self.questions = questions
        self.index = 0
        self.answers = []

        self.label = tk.Label(root, text="", font=("Arial", 16))
        self.label.pack(padx=20, pady=20)

        # Create a frame to hold the radio buttons and labels
        self.radio_frame = tk.Frame(root)
        self.radio_frame.pack(padx=20, pady=20)
        self.radio_value = tk.IntVar()

        btn_text = "Next" if self.index < len(self.questions) - 1 else "Finish"
        self.next_button = tk.Button(
            self.root, text=btn_text, command=self.store_answer
        )
        self.next_button.pack(pady=10)

        # update
        self.update()

    def store_answer(self):
        # Get selected value

        selected_value = self.radio_value.get()
        self.answers.append((self.questions[self.index - 1].text, selected_value))

        self.update()

    def update(self, event=None):
        if self.index >= len(self.questions):
            self.save_results()
            return

        question = self.questions[self.index]
        print(question)

        self.draw_buttons(question)

        self.index = self.index + 1
        self.label.config(text=question.text)

    def draw_buttons(self, question):
        # Clear existing radio buttons
        for widget in self.radio_frame.winfo_children():
            widget.destroy()

        self.radio_value.set(question.scale_size // 2 + 1)

        for i in range(1, question.scale_size + 1):
            radio_button = tk.Radiobutton(
                self.radio_frame,
                text=f"{i}",
                variable=self.radio_value,
                value=i,
                font=("Arial", 12),
            )
            radio_button.grid(row=0, column=i, padx=10)

        left_label = tk.Label(
            self.radio_frame, text=question.text_slider_min, font=("Ariel", 12)
        )
        left_label.grid(row=1, column=1, pady=(10, 0))

        right_label = tk.Label(
            self.radio_frame, text=question.text_slider_max, font=("Ariel", 12)
        )
        right_label.grid(row=1, column=question.scale_size, pady=(10, 0))

    def save_results(self):
        global CATEGORY
        print("save_results")

        if not os.path.exists("data"):
            os.makedirs("data")

        with open(f"data/{CATEGORY}_{formatted_time()}.txt", "w") as fp:
            fp.write(str(self.answers))
            fp.close()

        self.root.destroy()


def create_ui(questions):
    root = tk.Tk()
    root.title("Trust-ME")

    Poll(root, questions)

    root.mainloop()


def get_questions(category):
    global CATEGORY
    CATEGORY = category

    with open("questions.json", "r") as fp:
        fp = fp.read()
        qs = json.loads(fp)

        questions = []
        for q in qs[category]:
            questions.append(
                Question(
                    q["text"],
                    q["text_slider_min"],
                    q["text_slider_max"],
                    q["scale_size"],
                )
            )

        return questions


if __name__ == "__main__":
    questions = get_questions("engagement")
    create_ui(questions)
