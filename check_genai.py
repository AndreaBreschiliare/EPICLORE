import google.generativeai as genai
import os

# Try to get API key from environment or a placeholder if not set, 
# but the user's app uses st.secrets or input. 
# I'll try to list models if I can, but I might not have the key in this env.
# The user's `world_cloud.py` gets the key from st.text_input.

# Since I cannot interactively get the key here, I will rely on the user's claim 
# and the fact that they are running the app. 
# I will write a script that the user *could* run, but better yet, 
# I will modify the main app to include this model in the selection list 
# and implement the generation logic.

# However, to be safe, I'll check if the library has `ImageGenerationModel` or similar.
print(dir(genai))
