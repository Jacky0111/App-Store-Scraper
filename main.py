import asyncio
import glob
import os
import sys

from configs.app_id import (
    AD_APP_ID, AV_APP_ID, CF_APP_ID, CP_APP_ID, DE_APP_ID, EXNESS_APP_ID,
    HM_APP_ID, IB_APP_ID, PL_APP_ID, PU_APP_ID, RB_APP_ID, ST_APP_ID,
    VM_APP_ID, VT_APP_ID, XM_APP_ID, XTB_APP_ID,
)
from configs.countries import (
    ADSS_COUNTRIES, AV_COUNTRIES, CFI_COUNTRIES, CP_COUNTRIES, DE_COUNTRIES,
    EXNESS_COUNTRIES, HM_COUNTRIES, IB_COUNTRIES, PU_COUNTRIES, Plus_COUNTRIES,
    RB_COUNTRIES, Star_COUNTRIES, VM_COUNTRIES, VT_COUNTRIES, XM_COUNTRIES,
    XTB_COUNTRIES,
)

OUTPUT_DIR = "output"

# Maps brand name to (App Store App ID, list of storefront countries)
appstore_map = {
    'Vantage': (VM_APP_ID, VM_COUNTRIES),
    'VT Markets': (VT_APP_ID, VT_COUNTRIES),
    'PU Prime': (PU_APP_ID, PU_COUNTRIES),
    'StarTrader': (ST_APP_ID, Star_COUNTRIES),
    'XM': (XM_APP_ID, XM_COUNTRIES),
    'Exness': (EXNESS_APP_ID, EXNESS_COUNTRIES),
    'Deriv': (DE_APP_ID, DE_COUNTRIES),
    'AvaTrade': (AV_APP_ID, AV_COUNTRIES),
    'XTB': (XTB_APP_ID, XTB_COUNTRIES),
    'RoboForex': (RB_APP_ID, RB_COUNTRIES),
    'Hantec Markets': (HM_APP_ID, HM_COUNTRIES),
    'Interactive Brokers': (IB_APP_ID, IB_COUNTRIES),
    'CFI Financial': (CF_APP_ID, CFI_COUNTRIES),
    'Capital.com': (CP_APP_ID, CP_COUNTRIES),
    'ADSS': (AD_APP_ID, ADSS_COUNTRIES),
    'Plus500': (PL_APP_ID, Plus_COUNTRIES),
}


def display_menu():
    """Main menu for the system. Loops until the user chooses to quit."""
    while True:
        print('=========================')
        print('📱 App Store Review System')
        print('=========================')
        print('1. Scraper')
        print('2. AI Tagger')
        print('q. Quit')

        choice = input('Select an option (1-q): ')

        if choice == '1':
            scraper_menu()
        elif choice == '2':
            ai_tagger_menu()
        elif choice == 'q':
            print('👋 Exiting program. Goodbye!')
            sys.exit(0)
        else:
            print('❌ Invalid choice, please try again.')


def scraper_menu():
    """Submenu for scraping App Store reviews. Allows returning to the main menu with 'r'."""
    while True:
        print('\nScraper Menu')
        brands = list(appstore_map.keys())
        for i, brand in enumerate(brands, start=1):
            print(f'{i}. {brand}')
        print('r. Return to Main Menu')

        brand_choice = input('Select brand: ')

        if brand_choice == 'r':
            return

        if not brand_choice.isdigit() or int(brand_choice) not in range(1, len(brands) + 1):
            print('❌ Invalid brand choice.')
            continue

        brand = brands[int(brand_choice) - 1]

        from scraper.app_store import AppStoreScraper

        app_id, countries = appstore_map[brand]
        scraper = AppStoreScraper(app_id, countries, 'appstore', brand.lower().replace(' ', '_').replace('.', ''))
        scraper.run_scraper()

        print(f'✅ Completed scraping for {brand}.')
        input('Press Enter to return to the Scraper Menu...')


def ai_tagger_menu():
    """Submenu for running AI-based review categorization. Allows returning to the main menu with 'r'."""
    while True:
        print('\nAI Tagger Menu')
        csv_files = get_ai_tagger_files()

        if not csv_files:
            print(f'⚠️ No CSV files found in "{OUTPUT_DIR}" folder. Run the Scraper first.')
            input('Press Enter to return...')
            return

        for i, file in enumerate(csv_files, start=1):
            print(f'{i}. {os.path.basename(file)}')
        print('r. Return to Main Menu')

        file_choice = input('Select file: ')

        if file_choice == 'r':
            return

        if not file_choice.isdigit() or int(file_choice) not in range(1, len(csv_files) + 1):
            print('❌ Invalid file choice.')
            continue

        selected_file = csv_files[int(file_choice) - 1]
        output_file = selected_file.replace('.csv', '_categorized.csv')

        try:
            from ai_tagger.categorize import Args, categorize_reviews_async, get_bedrock_credentials, retry_unknowns

            get_bedrock_credentials()  # Fail fast with a clear message if AWS creds are missing.
        except ValueError as err:
            print(f'❌ {err}')
            input('Press Enter to return...')
            return

        args = Args()
        key_names = ['Content']
        company_name = os.path.basename(selected_file).split('_')[0]

        asyncio.run(categorize_reviews_async(
            input_path=selected_file,
            output_path=output_file,
            args=args,
            key_names=key_names,
            company_name=company_name,
        ))

        asyncio.run(retry_unknowns(
            output_path=output_file,
            args=args,
            key_names=key_names,
            company_name=company_name,
        ))

        print(f'✅ Categorization complete: {output_file}')
        input('Press Enter to return to the AI Tagger Menu...')


def get_ai_tagger_files():
    """Return all CSV files inside the output folder, sorted alphabetically."""
    if not os.path.exists(OUTPUT_DIR):
        return []

    files = glob.glob(os.path.join(OUTPUT_DIR, '*.csv'))
    files.sort(key=lambda f: os.path.basename(f).lower())

    return files


if __name__ == '__main__':
    display_menu()
