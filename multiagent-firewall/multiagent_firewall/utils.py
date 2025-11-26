def debug_invoke(app, inputs):
    final_state = None
    print("\n--- Starting Execution ---\n")

    for chunk in app.stream(inputs, stream_mode="updates"):
        for node, update in chunk.items():
            print(f"✅ Node '{node}' finished.")
            print(f"   Update: {update}\n")
            final_state = update

    return final_state
