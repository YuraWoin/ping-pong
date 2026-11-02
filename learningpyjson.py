from customtkinter import *

win = CTk()
win.geometry("400x400")
win.title("My menu")

diff = ["Easy", "Medium", "Hard"]
current_index = 0



#!! Заголовок у вигляді тексту на екрані - "Моє меню", "Вибір складності"

diff_label = CTkLabel(
    win,
    text= f"Diffuculty: - {diff[current_index]}",
    font = ("Arial", 24)
)

diff_label.pack(pady=10)



#!! Зробити кнопку "Грати" при настиканні на яку в терміналі пишеться повідомлення - Ви увійшли в гру

def exit_game():
    win.destroy()

exit_button = CTkButton(
    win,
    text="Exit",
    width=200,
    height=50,
    command=exit_game
)

exit_button.pack(pady = 10)

win.mainloop()
