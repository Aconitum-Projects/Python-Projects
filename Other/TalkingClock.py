import datetime
import playsound3
import gtts
import getpass

user = getpass.getuser()
salutation = "Hi"
file = open("C:/Users/Admin/Documents/Python/todo.txt")
todoList = file.readlines()
file.close()
actualTime = datetime.datetime.now()

if actualTime.hour >= 17:
    salutation = "Good evening"
elif actualTime.hour < 12:
    salutation = "Good morning"
    
if todoList:
    formattedTodos = "\n".join([f"- {task}" for task in todoList])
else:
    formattedTodos = "Nothing! You're free."
    
text = (
    f"\n\n\n{salutation} {user}, it's {actualTime.hour} and {actualTime.minute} minutes."
    f"\nHere is what you still have to do today:\n\n{formattedTodos}"
)

print(text)
tts = gtts.gTTS(text)
tts.save("tts.mp3")
playsound3.playsound("tts.mp3")