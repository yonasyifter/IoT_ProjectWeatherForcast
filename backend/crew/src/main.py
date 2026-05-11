from crew.src.crew import run_crew

def run(query: str, language: str = "en", device_data: str = "", context_data: str = ""):
    result = run_crew(
        device_data=device_data,
        user_query=query,
        language=language,
        context_data=context_data
    )
    return result

if __name__ == "__main__":
    print(run("What is the park temperature?", "en"))
