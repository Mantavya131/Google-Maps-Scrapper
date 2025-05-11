# --- START OF COMPLETE SCRIPT (Navigate, Search, Robust Scroll + Retry on No New Links, Collect All Links) ---

print("--- Starting Google Maps Business Link Scraper Script (Updated for Scrolling Retries) ---")

# --- Installation Steps ---
# Update apt-get and install Google Chrome and dependencies for virtual display
print("\n--- Step 1: Installing System Dependencies ---")
print("Updating apt-get and installing wget, xvfb, and attempting Google Chrome setup...")
try:
    # Update apt-get
    !apt-get update

    # Install wget and xvfb (for virtual display)
    !apt-get install -y wget xvfb
    print("System dependencies (wget, xvfb) installation/check complete.")

    # Check if Chrome is already installed and is the correct architecture
    chrome_version_check = !google-chrome --version 2>&1
    print(f"Google Chrome version check result: {chrome_version_check}")
    chrome_installed_correctly = False
    if chrome_version_check and "Google Chrome" in chrome_version_check[0]:
        print("Google Chrome seems to be installed.")
        chrome_installed_correctly = True
    else:
        print("Google Chrome not detected or not in expected path. Proceeding with download and install.")

    if not chrome_installed_correctly:
        # Download Google Chrome .deb package
        print("Downloading Google Chrome .deb package...")
        # Using -O to specify the output filename to avoid .1 suffix
        !wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O google-chrome-stable_current_amd64.deb
        print("Google Chrome package download complete.")

        # Install the downloaded package
        print("Installing Google Chrome...")
        !dpkg -i google-chrome-stable_current_amd64.deb
        print("dpkg installation command executed.")

        # Fix broken dependencies - crucial for Chrome installation to complete
        print("Fixing broken dependencies...")
        !apt-get install -f -y
        print("Dependency fix command executed.")
        print("Google Chrome installation attempted.")
    else:
        print("Skipping Google Chrome download/install as it appears to be present.")

    print("Step 1: System dependencies and Google Chrome setup complete.")

except Exception as e:
    print(f"--- ERROR during Step 1: System Dependency or Chrome Installation Failed ---")
    print(f"Error details: {e}")
    print("Please check the output above for specific installation errors.")
    # Continue to Python package installation


# Install Python packages
print("\n--- Step 2: Installing Python Packages ---")
print("Installing Python packages (selenium, beautifulsoup4, pandas, requests, webdriver-manager, pyvirtualdisplay)...")
try:
    # Include all packages needed for potential future steps or robust handling
    !pip install selenium beautifulsoup4 pandas requests webdriver-manager pyvirtualdisplay
    print("Step 2: Python package installation complete.")
except Exception as e:
    print(f"--- ERROR during Step 2: Python Package Installation Failed ---")
    print(f"Error details: {e}")
    print("Please ensure you have network access and pip is working correctly.")
    # Installation failure here will likely cause import errors later.


# --- Import libraries ---
print("\n--- Step 3: Importing Libraries ---")
try:
    import time
    import re
    import pandas as pd
    import requests
    from bs4 import BeautifulSoup
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    # from google.colab import files # Import for Colab download (uncomment if needed)
    import urllib.parse
    from pyvirtualdisplay import Display # Import Display
    print("Step 3: Libraries imported successfully.")
except Exception as e:
    print(f"--- ERROR during Step 3: Library Import Failed ---")
    print(f"Error details: {e}")
    print("Please ensure all necessary Python packages were installed correctly in Step 2.")
    # If imports fail, the script cannot proceed.
    # Consider adding a sys.exit() here in a non-notebook environment.


# Function to set up the Chrome driver with Virtual Display
def setup_driver():
    print("\n--- Step 4: Setting up Selenium Driver and Virtual Display ---")
    display = None
    driver = None
    try:
        print("Starting virtual display...")
        # Using a common screen size, visible=0 for headless
        display = Display(visible=0, size=(1280, 720))
        display.start()
        print("Virtual display started.")

        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # Use a common user agent string to appear more like a real browser
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        # Optional: Arguments to reduce detection risks
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--disable-extensions")
        # Point binary location (essential for some environments like Colab)
        chrome_options.binary_location = "/usr/bin/google-chrome"
         # Add argument to allow remote origin - sometimes necessary in Colab/headless
        chrome_options.add_argument("--remote-allow-origins=*")
         # Add argument to ignore certificate errors if needed (use with caution)
        # chrome_options.add_argument('--ignore-certificate-errors')
        # Added arguments for stability in headless mode - attempt to fix crash
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-zygote")


        print("Installing/locating chrome driver executable and initializing Selenium...")
        # Use ChromeDriverManager to automatically get the correct driver version
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as driver_e:
            print(f"--- ERROR: Chrome Driver Manager failed: {driver_e} ---")
            print("Attempting to use a static path fallback...")
            try:
                service = Service("/usr/local/bin/chromedriver") # Common fallback path
                driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as fallback_e:
                print(f"--- ERROR: Fallback driver path also failed: {fallback_e} ---")
                driver = None # Ensure driver is None if both fail


        if driver:
            print("Step 4: Driver setup successful.")
            # Optional: Set implicit wait (can be combined with explicit waits)
            driver.implicit_wait = 5 # Wait up to 5 seconds for elements if not found immediately
        else:
            print("Step 4: Driver setup failed.")


        return driver, display

    except Exception as e:
        print(f"--- ERROR during Step 4: Driver or Virtual Display Setup Failed ---")
        print(f"Error details: {e}")
        print("This could be due to Chrome installation issues, incompatible driver versions, or environment problems.")
        if display:
            try:
                display.stop()
            except:
                pass
        return None, None

# --- FUNCTION TO NAVIGATE, SEARCH, SCROLL, AND COLLECT ALL ITEM LINKS ---
# This function navigates, searches, finds the list container,
# scrolls through the list to load all items, and collects their detail page links.
# Uses robust scrolling, end detection, and retries on no new links based on provided HTML structure.
def navigate_search_and_collect_all_item_links(driver, query="hotels in ny 10016"):
    if not driver:
        print("--- Skipping process: Driver is not available. ---")
        return [] # Indicate failure by returning empty list

    # Define the Google Maps base URL
    maps_base_url = "https://www.google.com/maps"
    search_input_id = "searchboxinput" # ID from provided HTML
    search_button_id = "searchbox-searchbutton" # ID from provided HTML
    # Selector for the main scrollable results list container
    # Based on provided HTML, div[role="feed"] is the correct scrollable element
    business_list_container_locator = (By.CSS_SELECTOR, 'div[role="feed"]') # Confirmed by provided HTML
    # Selector for individual clickable item links
    # Based on provided HTML, 'a.hfpxzc' is the correct link selector
    business_item_link_selector = 'a.hfpxzc' # Confirmed by provided HTML
    # Locator for the "End of list" message based on provided HTML
    # The structure `div.m6QErb.XiKgde.tLjsW.eKbjU` was confirmed
    end_of_list_locator = (By.CSS_SELECTOR, 'div.m6QErb.XiKgde.tLjsW.eKbjU') # Confirmed by provided HTML


    # --- Step 5-8: Navigate, Search Input, and Submission ---
    print(f"\n--- Steps 5-8: Navigating to Google Maps and Performing Search ---")
    try:
        print(f"Navigating to URL: {maps_base_url}")
        driver.get(maps_base_url)
        print("Navigation command sent. Waiting for page load...")

        # Wait for and find the search input field using its ID
        print(f"Waiting for search input element with ID: '{search_input_id}'")
        search_input_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, search_input_id))
        )
        print("Search input field found.")

        # Enter the search query
        print(f"Entering query: '{query}'")
        search_input_element.clear() # Clear any existing text
        search_input_element.send_keys(query)
        print("Query entered.")

        # Wait for and find the search button using its ID, then click
        print(f"Waiting for search button with ID: '{search_button_id}'")
        search_button_element = WebDriverWait(driver, 10).until(
             EC.element_to_be_clickable((By.ID, search_button_id))
        )
        print("Search button found. Clicking...")
        search_button_element.click()
        print("Search button clicked.")

        # Wait for the search results list panel to load after clicking search
        print(f"Waiting for search results list container to appear (using locator: {business_list_container_locator})...")
        business_list_element = WebDriverWait(driver, 30).until( # Increased wait for initial results
            EC.presence_of_element_located(business_list_container_locator)
        )
        print("Business list container found.")
        time.sleep(3) # Small buffer after list appears

        # Check if we landed directly on a business page instead of the list
        current_url = driver.current_url
        if '/place/' in current_url and '/search/' not in current_url:
             print("Detected direct navigation to a single business page. This script expects a search results list.")
             # The script will attempt to proceed assuming the list element was still found (which might happen
             # if the list is embedded below the main detail, but usually not).
             # A more robust script might stop here or try navigating back.
             pass


    except Exception as e:
         print(f"--- ERROR during Steps 5-8: An error occurred during initial navigation or waiting for elements ---")
         print(f"Error details: {e}")
         return [] # Stop here if initial steps failed


    # --- Step 9 & 10: Scrolling and Collecting ALL Item Links ---
    print(f"\n--- Step 9 & 10: Starting Robust Scrolling and Collecting ALL Item Links ---")

    collected_links_set = set() # Use a set to store unique links
    scroll_pause_time = 2 # Adjusted wait time after each scroll (can be tuned)
    scroll_attempts = 0
    max_scroll_attempts = 1000 # Safety break
    # --- ADDED for retry logic ---
    consecutive_no_new_links = 0
    max_consecutive_no_new_links = 3 # Stop after 3 scrolls yield no *new unique* links (initial check + 2 retries)
    # --- END ADDED ---


    print("Starting scrolling process...")
    try:
        # Ensure the list container element is valid before starting the loop
        # Re-find the list element to avoid StaleElementReferenceException
        business_list_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(business_list_container_locator)
        )
        print("Ready to begin scrolling loop.")

        while True:
            # --- Re-find elements and collect links in the loop ---
            # Re-find the list element each iteration
            try:
                 business_list_element = WebDriverWait(driver, 10).until(
                     EC.presence_of_element_located(business_list_container_locator)
                 )
                 # Wait until at least one link element is present within the list
                 # Use a shorter wait here as we are mid-scroll
                 WebDriverWait(business_list_element, 5).until(
                      EC.presence_of_element_located((By.CSS_SELECTOR, business_item_link_selector))
                 )
            except Exception as e:
                 print(f"Warning: Could not re-find list container or find any link elements in scroll loop: {e}. This might indicate the list disappeared or is empty.")
                 break # Exit loop if list element or links within are not found/stale

            # Store the number of links before collecting in this iteration
            previous_total_unique_links = len(collected_links_set)

            # Find all current item link elements visible in the list container
            item_link_elements = business_list_element.find_elements(By.CSS_SELECTOR, business_item_link_selector)
            # print(f"Found {len(item_link_elements)} links on current view.")

            # Collect hrefs of link elements currently in view and add to set
            for element in item_link_elements:
                try:
                    link_href = element.get_attribute('href')
                    if link_href:
                        collected_links_set.add(link_href)
                except Exception as e:
                    # Handle potential stale element reference or other issues
                    pass # Silently skip problematic elements

            current_total_unique_links = len(collected_links_set)
            print(f"Scroll attempt {scroll_attempts + 1}: Total unique links found so far: {current_total_unique_links}")


            # *** Primary Stop Condition: Check for End of List Message ***
            try:
                # Use find_elements to avoid exception if not present
                end_element = driver.find_elements(By.CSS_SELECTOR, end_of_list_locator[1])
                if end_element:
                    print("Detected 'End of list' element. Stopping scroll.")
                    break # Exit the while loop
            except Exception as e:
                # This catch is less likely with find_elements but good practice
                print(f"Error checking for end element: {e}")
                pass


            # *** Secondary Stop Condition: Check for Progress ***
            # If no new unique links were added in this iteration
            if current_total_unique_links == previous_total_unique_links:
                 consecutive_no_new_links += 1
                 print(f"No new unique links found in this scroll step. Consecutive attempts with no new links: {consecutive_no_new_links}/{max_consecutive_no_new_links}")
            else:
                 # Progress was made, reset the counter
                 consecutive_no_new_links = 0

            # If we've had too many consecutive scrolls with no new links, assume we're at the end or stuck
            if consecutive_no_new_links >= max_consecutive_no_new_links:
                print(f"Reached {max_consecutive_no_new_links} consecutive attempts with no new links. Assuming end of list or stuck. Stopping scroll.")
                break # Exit loop


            # Safety break for infinite loops (based on total scroll attempts)
            if scroll_attempts >= max_scroll_attempts:
                print(f"Warning: Reached maximum scroll attempts ({max_scroll_attempts}). Stopping scroll.")
                break # Exit loop

            scroll_attempts += 1 # Increment scroll attempt counter

            # *** Scroll Method ***
            # Scroll the list container by scrolling the last found element into view
            try:
                print(f"Scrolling last element into view (Attempt {scroll_attempts})...")
                item_link_elements = business_list_element.find_elements(By.CSS_SELECTOR, business_item_link_selector)
                if item_link_elements: # Ensure there's at least one element to scroll to
                     last_item = item_link_elements[-1] # Get the last element found
                     driver.execute_script("arguments[0].scrollIntoView(true);", last_item)
                else:
                     # Fallback if no items found, try scrolling the container itself a bit
                     driver.execute_script("arguments[0].scrollTop += arguments[0].clientHeight * 0.8;", business_list_element) # Scroll by 80% of viewable height


            except Exception as scroll_e:
                 print(f"--- ERROR during scroll attempt {scroll_attempts}: {scroll_e}. Cannot scroll.")
                 break # Exit loop if scrolling fails


            # Wait for new items to load after scrolling
            print(f"Waiting for {scroll_pause_time} seconds for new items to load...")
            time.sleep(scroll_pause_time) # Adjust this wait time based on observation


    except Exception as e:
        # This catches unexpected errors in the main scrolling loop body
        print(f"--- UNEXPECTED ERROR during Step 9 & 10: An error occurred during scrolling and collection ---")
        print(f"Error details: {e}")
        print("Attempting to stop scrolling and continue with links collected so far.")


    print(f"\n--- Finished Robust Scrolling and Collecting Item Links ---")
    print(f"Final number of unique item links collected: {len(collected_links_set)}")

    # Return the list of unique collected links
    return list(collected_links_set) # Convert set back to list for processing


# --- Main Process: Navigate, Search, Scroll, Collect Links Only, Export ---
# This function orchestrates the process of collecting all business links via scrolling.
# Returns the list of links.
def run_full_extraction_process(query="hotels in ny 10016", csv_filename="Maps_business_links.csv"):
    print("--- Step 0: Starting Full Link Extraction Process ---")
    # Call the setup function
    driver, display = setup_driver()

    # Check if driver setup was successful
    if not driver:
        print("--- Process Aborted: Driver setup failed. ---")
        if display:
            try:
                display.stop()
            except: pass
        return [] # Return empty list on failure

    # List to store unique collected detail page links
    collected_links = []
    df = pd.DataFrame(columns=['Business Link']) # Initialize empty DataFrame outside try

    try: # Use a try block for the main process to ensure cleanup happens
        # --- Steps 5-10: Navigate, Search, Robust Scroll, and Collect ALL Item Links ---
        collected_links = navigate_search_and_collect_all_item_links(driver, query=query)

        # --- Step 11: Creating DataFrame from Links (Inside the function now) ---
        print(f"\n--- Step 11: Creating DataFrame from Collected Links ---")
        if collected_links:
            # Create a DataFrame with a single column for the links
            df = pd.DataFrame(collected_links, columns=['Business Link'])
            print(f"DataFrame created with {len(df)} links.")
        else:
            print("No links were collected, creating empty DataFrame.")
            # df is already initialized as empty DataFrame with column

        # --- Step 12: Exporting Data to CSV (Inside the function now) ---
        print(f"\n--- Step 12: Exporting Data to CSV ---")
        # Export only if DataFrame is not empty
        if not df.empty:
            try:
                csv_filename = csv_filename # Use the filename passed to the function
                df.to_csv(csv_filename, index=False)
                print(f"Data successfully saved to '{csv_filename}'")
                 # If running in Google Colab, you can download the file:
                 # try:
                 #     from google.colab import files # Ensure this is imported
                 #     files.download(csv_filename)
                 #     print(f"Attempting to download '{csv_filename}'...")
                 # except ImportError:
                 #     print("Running outside Colab, skipping auto-download.")
                 # except Exception as download_e:
                 #     print(f"Could not initiate download in Colab: {download_e}")

            except Exception as e:
                print(f"--- ERROR during Step 12: Failed to save data to CSV ---")
                print(f"Error details: {e}")
        else:
            print("DataFrame is empty. Skipping CSV export.")


        # --- Step 13: Reporting and Displaying Final Collected Links (Inside the function now) ---
        print(f"\n--- Step 13: Reporting and Displaying Final Collected Links ---")
        print(f"Total links collected: {len(collected_links)}") # Report based on the list itself
        if not df.empty: # Check if DataFrame is not empty
             print("\nCollected Links (All rows):")

             # Ensure pandas options allow full display for this final print
             pd.set_option('display.max_rows', None)
             pd.set_option('display.max_columns', None)
             # pd.set_option('display.width', None) # Optional

             try:
                 from IPython.display import display
                 print(df.to_markdown(index=False))
             except ImportError:
                  print(df)

             # Optional: Reset display options afterwards if needed
             # pd.reset_option('display.max_rows')
             # pd.reset_option('display.max_columns')
             # pd.reset_option('display.width')

        else:
            print("No links to display.")


    except Exception as e:
        # Catching unexpected exceptions during the process
        print(f"\n--- UNEXPECTED ERROR during full extraction process ---")
        print(f"Error details: {e}")
        print("Attempting cleanup and returning collected links so far.")
        # df will already be initialized or populated, no need to recreate here.


    finally: # This block always runs whether there was an error or not
        print("\n--- Step 14: Cleaning up Selenium Driver and Virtual Display ---")
        if driver:
            try:
                driver.quit()
                print("Selenium driver closed.")
            except Exception as e:
                print(f"--- ERROR during Step 14: Error closing driver ---")
                print(f"Error details: {e}")

        if display:
            try:
                display.stop()
                print("Virtual display stopped.")
            except Exception as e:
                print(f"--- ERROR during Step 14: Error stopping virtual display ---")
                print(f"Error details: {e}")

    # Return the list of collected links
    return collected_links

# --- Run the Full Link Extraction Process ---
# Define the simple query to search for and the output CSV filename
# CHANGE THIS QUERY to what you want to search for!
search_query_to_run = "doctor clinics in New York, NY 10036" # <--- CHANGE THIS
output_csv_filename = "Maps_hotel_links_scrolled.csv" # Changed filename to indicate it scrolled

print(f"\n--- Running the Full Google Maps Link Extraction Process for '{search_query_to_run}' ---")
# Execute the main process function and store the returned list of links
# This function will now navigate, search, *scroll* the list, and collect all links.
business_links_to_scrape_10036 = run_full_extraction_process(query=search_query_to_run, csv_filename=output_csv_filename) # <--- Links stored here

print("\n--- Overall Full Link Extraction Process Finished ---")
print(f"Final list 'business_links_to_scrape_10036' contains {len(business_links_to_scrape_10036)} links.")
if business_links_to_scrape_10036: # Check if the list is not empty
     print(f"Links should also be saved to '{output_csv_filename}' and potentially downloaded.")
else:
     print("No links were collected.")


# The 'business_links_to_scrape' list now holds the collected URLs.
# You can access the links from this list directly, e.g.:
# first_link = business_links_to_scrape[0]
# for link in business_links_to_scrape:
#     print(link)

# If you need the DataFrame separately after this run, you would recreate it from the list:
# final_collected_links_df_from_list = pd.DataFrame(business_links_to_scrape, columns=['Business Link'])


# --- END OF COMPLETE SCRIPT (Navigate, Search, Robust Scroll + Retry on No New Links, Collect All Links) ---
