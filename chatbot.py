#importing streamlit
import streamlit as st

#importing all relevant libraries for the conversation manager class
pip install openai
from openai import OpenAI
import tiktoken
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get('API_KEY')


#creating ConversationManager class 

class ConversationManager:
    def __init__(self, api_key,base_url="https://openai-api.dataquest.io/v1", model="models/openhermes-2.5-mistral-7b", default_temperature=0.7, default_max_tokens=500, token_budget=1000, history_file=None):
        self.client = OpenAI(api_key=api_key)
        self.client.base_url = base_url
        self.model = model
        self.temperature = default_temperature
        self.max_tokens = default_max_tokens
        self.token_budget = token_budget
        self.system_messages = {"sassy_assistant":"You are a sassy assistant who is fed up with answering questions.",
                                "angry_assistant": "You are an angry assistant. You give unfriendly ansers and yell your response in all caps.",
                                "thoughtful_assistant": "You are a thoughtful assistant, always ready to dig deeper. \
                                You ask clarifying questions to ensure understanding and approach problems with a step-by-step methodology.",
                                "friendly_assistant":"You are a friendly assistant who is enjoying answering questions.",
                               "funny_assistant":"You are a helpful and funny assistant wrapping every response in a joke.",
                               "custom":"Enter custom message"}
        
        
        #setting default persona
        self.system_message = self.system_messages["sassy_assistant"] 

        #initializing history file if not specified
        if history_file == None:
            time = datetime.now()
            self.history_file =  f'{time.strftime("%Y-%m-%d-%H-%M-%S")}_conversation_history'
        else:
            self.history_file = history_file
                
        self.load_conversation_history()
    
    def load_conversation_history(self):
        try:
            with open(self.history_file, "r") as file:
                self.conversation_history = json.load(file)
        except FileNotFoundError:
            self.conversation_history = [{"role": "system", "content": self.system_message}]
        except json.JSONDecodeError:
            print("Error reading the conversation history file. Starting with an empty history.")
            self.conversation_history = [{"role": "system", "content": self.system_message}]
            
    def save_conversation_history(self):
        try:
            with open(self.history_file, "w") as file:
                json.dump(self.conversation_history, file, indent=4)
        except IOError:
            print("An unexpected error occurred trying to save conversation history.")
        except Exception:
            print("An unexpected error occurred.")
            
    def clear_chat_history(self):
        self.conversation_history = [{"role": "system", "content": self.system_message}]
        self.save_conversation_history()
    
    def set_persona(self,persona):
        if persona in self.system_messages:
            self.system_message = self.system_messages[persona]
            self.update_system_message_in_history()
            
        else:
            raise ValueError(f"Unknown persona: {persona}. Available personas are: {list(self.system_messages.keys())}")
    
    def set_custom_system_message(self,custom_message):
        if not custom_message:
            print("Custom message can not be empty!")
        else:
            self.system_messages['custom'] = custom_message
            self.set_persona('custom')
    
    def update_system_message_in_history(self):
        if self.conversation_history and self.conversation_history[0]['role'] == 'system':
            self.conversation_history[0]['content'] = self.system_message
        else:
            self.conversation_history.insert(0, {"role":"system", "content": self.system_message})
                    
                             
    def count_tokens(self,text):
        try:
            encoding = tiktoken.encoding_for_model(self.model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        
        num_tokens = len(encoding.encode(text))
        return num_tokens
    
    def total_tokens_used(self):
        self.token_count = sum(self.count_tokens(message["content"]) for message in self.conversation_history)
        return self.token_count
        
    def enforce_token_budget(self):
        while self.total_tokens_used() > self.token_budget:
            if len(self.conversation_history) <= 1:
                break
            self.conversation_history.pop(1)
            
    
    def chat_completion(self,prompt,temperature=None,max_tokens=None):
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens if max_tokens is not None else self.max_tokens
        
        self.conversation_history.append({"role":"user", "content": prompt})
        messages = self.conversation_history
        
        self.enforce_token_budget()
        
        try:
            response = self.client.chat.completions.create(model=self.model, temperature=temperature, max_tokens=max_tokens, messages=messages)
        except Exception as e:
            print(f"An error occured generating a response: {e}")
            return None
        
        ai_response = response.choices[0].message.content
        self.conversation_history.append({"role":"assistant", "content": ai_response})
        
        self.save_conversation_history()
        
        return ai_response
        
#configuring the streamlit app

st.title("My Little Chatbot")

if 'chat_manager' not in st.session_state:
    st.session_state['chat_manager'] = ConversationManager(api_key)
    
if 'conversation_history' not in st.session_state:
    st.session_state['conversation_history'] = st.session_state['chat_manager'].conversation_history
    
#setup sidebar
st.sidebar.title("Customize the bot!")
custom_token_budget = st.sidebar.slider("Set token budget", 200, 2000, 500)
custom_temperature = st.sidebar.slider("Set temperature", 0.1,2.0,0.7)
selected_persona = st.sidebar.selectbox("Select a persona for the chatbot", ["Sassy Assistant", "Angry Assistant", "Thoughtful Assistant", "Friendly Assistant", "Funny Assistant", "Custom Assistant"])
if selected_persona == "Custom Assistant":
        custom_message = st.sidebar.text_input("Enter your custom assistant description here")
        st.session_state['chat_manager'].set_custom_system_message(custom_message)
elif selected_persona == "Sassy Assistant":
    st.session_state['chat_manager'].set_persona("sassy_assistant")
elif selected_persona == "Angry Assistant":
    st.session_state['chat_manager'].set_persona("angry_assistant")
elif selected_persona == "Thoughtful Assistant":
    st.session_state['chat_manager'].set_persona("thoughtful_assistant")
elif selected_persona == "Friendly Assistant":
    st.session_state['chat_manager'].set_persona("friendly_assistant")
elif selected_persona == "Funny Assistant":
    st.session_state['chat_manager'].set_persona("funny_assistant")
      
if st.sidebar.button("Clear Chat"):
    st.session_state['chat_manager'].clear_chat_history()
    st.session_state['conversation_history'] = st.session_state['chat_manager'].conversation_history        

#setting up the chat functionality

user_input = st.chat_input("Write your message")

if user_input:
    st.session_state['chat_manager'].chat_completion(user_input,temperature=custom_temperature, max_tokens=custom_token_budget)

for message in st.session_state['conversation_history']:
    if message['role'] == 'system':
        pass
    else:
        with st.chat_message(message['role']):
            st.write(message['content'])
