<p align="center"><img height="300" alt="Intuition Logotype" src="https://github.com/user-attachments/assets/827d56b8-526c-4777-bed2-204210ad927f" /></p>

# intuition

**Intuition** is a suite of tools to assist with image generation, remixing, and magic prompt generation with the API for the high-quality Ideogram v4 image generator.

There are two tools:

* **Web** -- This tool has an interactive editor with bounding box drawing and global scene settings along with supporting loading and saving of settings. It generates Ideogram v4 compatible JSON objects on the fly.
* **CLI** -- This tool (`ideogram.py`) is a command-line Python script with full API support with Generate, Remix, Magic Prompt, and Describe modalities. It takes your API key as an environment variable and support options via attributes for the respective modalities.

I can strongly recommend using these two tools in tandem for a basic Ideogram v4 API workflow on Windows, macOS or Linux. Simply copy & paste the JSON from the editor into a text file you keep open, and happy generating!

I first intended to take this the whole nine yards with API calling and downloading the results from within the web editor itself, but thought it'd be easier for redistribution and _ad hoc_ use to focus on the JSON (the hard part and what it does best), leaving the user free to combine this tool with anything else and more easily integrate it in other workflows. The issue with a full-fledged web app like this is that you need to cover for CORS issues and thus host it yourself somewhere; you can't just download a HTML file to your laptop.
