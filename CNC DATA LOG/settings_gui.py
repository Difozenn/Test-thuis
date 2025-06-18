import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import threading
from datetime import datetime, date, timedelta
import logging
import matplotlib.pyplot as plt
from collections import defaultdict

# Attempt to import matplotlib, with a fallback if not installed
try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("[WARNING] Matplotlib is not installed. Statistics graphs will not be available.")

# Import runtime statistics from hops_file_logger
# These will be populated when hops_file_logger.py runs
from hops_file_logger import (
    CONFIG, get_program_start_time, 
    get_runtime_category_totals, get_runtime_daily_item_counts, # Using getters
    BASE_DIR, CATEGORIES_FILE, SEEN_ENTRIES_FILE, EVENT_HISTORY_FILE as HFL_EVENTS_FILE # Import EVENT_HISTORY_FILE path from hops_file_logger
)

CONFIG_FILE = 'logger_config.json'
CATEGORIES_FILE = 'categories.json'
# EVENTS_FILE = 'events_history.json' # Use HFL_EVENTS_FILE from hops_file_logger for consistency

class SettingsWindow(tk.Toplevel):
    def __init__(self, master=None):
        self.log_refresh_id = None
        self.stats_refresh_id = None
        self.category_canvas = None
        self.daily_canvas = None
        super().__init__(master)
        self.title("Instellingen")
        try:
            self.icon_image = tk.PhotoImage(file='ico.png')
            self.iconphoto(True, self.icon_image)
        except tk.TclError:
            print("[WARNING] Could not load ico.png for SettingsWindow icon.")
        self.geometry("600x450")
        self.resizable(True, True)
        self.attributes('-topmost', True)

        self.last_log_timestamp = "" # For highlighting new log entries

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        # Create tabs
        self.tab_scan_files = ttk.Frame(self.notebook)
        self.tab_categories = ttk.Frame(self.notebook)
        self.tab_event_log = ttk.Frame(self.notebook)
        self.tab_statistics = ttk.Frame(self.notebook) # New Statistics Tab

        self.notebook.add(self.tab_scan_files, text="Scan Mappen")
        self.notebook.add(self.tab_categories, text="Categorieën")
        self.notebook.add(self.tab_event_log, text="Logboek")
        self.notebook.add(self.tab_statistics, text="Statistieken") # Add to notebook

        # Populate tabs
        self.create_scan_files_tab()
        self.create_categories_tab()
        self.create_event_log_tab()
        self.create_statistics_tab() # Create the new tab content

        self.protocol("WM_DELETE_WINDOW", self.close_window)
        self.bind("<<SafeDestroy>>", self._perform_destroy_event)
        self.focus_force()

    def _perform_destroy_event(self, event=None): # Added event=None for direct calls if needed
        logging.info(f"_perform_destroy_event called for {event.widget if event else 'direct call'}.")
        # This is called via event_generate from another thread or by <<SafeDestroy>> binding.
        self._perform_destroy()

    def _perform_destroy(self):
        logging.info("Performing settings window destruction.")
        # Cancel pending 'after' jobs
        if hasattr(self, 'log_refresh_id') and self.log_refresh_id:
            try: self.after_cancel(self.log_refresh_id)
            except tk.TclError: logging.debug("TclError cancelling log_refresh_id")
            self.log_refresh_id = None
        if hasattr(self, 'stats_refresh_id') and self.stats_refresh_id:
            try: self.after_cancel(self.stats_refresh_id)
            except tk.TclError: logging.debug("TclError cancelling stats_refresh_id")
            self.stats_refresh_id = None

        # Clean up matplotlib figures and canvases
        if hasattr(self, 'category_canvas') and self.category_canvas:
            try:
                figure_ref = self.category_canvas.figure # Store ref before canvas is gone
                self.category_canvas.get_tk_widget().destroy()
                if figure_ref: plt.close(figure_ref)
            except Exception as e:
                logging.error(f"Error closing category canvas/figure: {e}")
            self.category_canvas = None
        if hasattr(self, 'daily_canvas') and self.daily_canvas:
            try:
                figure_ref = self.daily_canvas.figure
                self.daily_canvas.get_tk_widget().destroy()
                if figure_ref: plt.close(figure_ref)
            except Exception as e:
                logging.error(f"Error closing daily canvas/figure: {e}")
            self.daily_canvas = None

        # Replace the icon with a dummy image before destroying the window
        # This prevents the RuntimeError on exit.
        if hasattr(self, 'icon_image'):
            try:
                dummy_image = tk.PhotoImage(width=1, height=1)
                self.iconphoto(True, dummy_image)
                self.icon_image = dummy_image # Keep a reference
            except tk.TclError:
                logging.debug("TclError while clearing icon, window likely already destroyed.")

        # Destroy the window itself
        if self.winfo_exists():
            self.destroy()

    def close_window(self):
        # This method is called when the window's 'X' button (WM_DELETE_WINDOW) is pressed.
        logging.info("SettingsWindow close_window (WM_DELETE_WINDOW) called.")
        logging.info("Requesting safe destruction of SettingsWindow via event from close_window.")
        self.event_generate("<<SafeDestroy>>") # Ensure it's processed by the event loop

    def request_close_from_external(self):
        # This method is designed to be called from another thread (e.g., the main tray icon thread).
        logging.info("SettingsWindow close requested from external thread.")
        if self.winfo_exists():
            try:
                # Generate an event that will be handled by _perform_destroy_event in the window's own thread.
                self.event_generate("<<SafeDestroy>>")
            except tk.TclError as e:
                # This can happen if the window is already in the process of being destroyed.
                logging.error(f"TclError generating <<SafeDestroy>> event: {e}. Window might be closing.")
        else:
            logging.info("Settings window does not exist or already destroyed, no need to generate <<SafeDestroy>>.")

    # --- Utility Functions ---
    def load_json(self, file_path):
        if not os.path.exists(file_path):
            return {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def save_json(self, data, file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        messagebox.showinfo("Opgeslagen", f"{os.path.basename(file_path)} is bijgewerkt.", parent=self)

    # --- Scan Files Tab ---
    def create_scan_files_tab(self):
        frame = self.tab_scan_files
        
        list_frame = ttk.LabelFrame(frame, text="Te scannen mappen")
        list_frame.pack(padx=10, pady=10, fill='both', expand=True)

        self.scan_files_listbox = tk.Listbox(list_frame)
        self.scan_files_listbox.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.scan_files_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.scan_files_listbox.config(yscrollcommand=scrollbar.set)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(btn_frame, text="Toevoegen", command=self.add_scan_file).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Verwijderen", command=self.remove_scan_file).pack(side='left', padx=5)
        
        self.load_scan_files()

    def load_scan_files(self):
        self.scan_files_listbox.delete(0, tk.END)
        config = self.load_json(CONFIG_FILE)
        for path in config.get('scan_files', []):
            self.scan_files_listbox.insert(tk.END, path)

    def add_scan_file(self):
        new_path = simpledialog.askstring("Nieuwe Map", "Voer het volledige pad van de map in:", parent=self)
        if new_path and os.path.isdir(new_path):
            config = self.load_json(CONFIG_FILE)
            scan_files = config.get('scan_files', [])
            if new_path not in scan_files:
                scan_files.append(new_path)
                config['scan_files'] = scan_files
                self.save_json(config, CONFIG_FILE)
                self.load_scan_files()
            else:
                messagebox.showwarning("Dubbel", "Dit pad staat al in de lijst.", parent=self)
        elif new_path:
            messagebox.showerror("Fout", "Het opgegeven pad is geen geldige map.", parent=self)

    def remove_scan_file(self):
        selected_indices = self.scan_files_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Geen selectie", "Selecteer een pad om te verwijderen.", parent=self)
            return
        
        selected_path = self.scan_files_listbox.get(selected_indices[0])
        if messagebox.askyesno("Bevestigen", f"Weet u zeker dat u '{selected_path}' wilt verwijderen?", parent=self):
            config = self.load_json(CONFIG_FILE)
            scan_files = config.get('scan_files', [])
            if selected_path in scan_files:
                scan_files.remove(selected_path)
                config['scan_files'] = scan_files
                self.save_json(config, CONFIG_FILE)
                self.load_scan_files()

    # --- Categories Tab ---
    def create_categories_tab(self):
        frame = self.tab_categories
        
        list_frame = ttk.LabelFrame(frame, text="Categorieën (Sleutelwoord -> Categorie)")
        list_frame.pack(padx=10, pady=10, fill='both', expand=True)

        self.cat_tree = ttk.Treeview(list_frame, columns=('Keyword', 'Category'), show='headings')
        self.cat_tree.heading('Keyword', text='Sleutelwoord')
        self.cat_tree.heading('Category', text='Categorie')
        self.cat_tree.pack(side='left', fill='both', expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.cat_tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.cat_tree.config(yscrollcommand=scrollbar.set)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(btn_frame, text="Toevoegen", command=self.add_category).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Verwijderen", command=self.remove_category).pack(side='left', padx=5)

        self.load_categories()

    def load_categories(self):
        for i in self.cat_tree.get_children():
            self.cat_tree.delete(i)
        categories = self.load_json(CATEGORIES_FILE)
        for keyword, category in categories.items():
            self.cat_tree.insert('', 'end', values=(keyword, category))

    def add_category(self):
        keyword = simpledialog.askstring("Nieuw Sleutelwoord", "Voer het sleutelwoord in:", parent=self)
        if not keyword: return
        
        category = simpledialog.askstring("Nieuwe Categorie", f"Voer de categorie voor '{keyword}' in:", parent=self)
        if not category: return

        categories = self.load_json(CATEGORIES_FILE)
        categories[keyword] = category
        self.save_json(categories, CATEGORIES_FILE)
        self.load_categories()

    def remove_category(self):
        selected_item = self.cat_tree.selection()
        if not selected_item:
            messagebox.showwarning("Geen selectie", "Selecteer een categorie om te verwijderen.", parent=self)
            return
        
        keyword_to_remove = self.cat_tree.item(selected_item[0])['values'][0]
        if messagebox.askyesno("Bevestigen", f"Weet u zeker dat u de categorie voor '{keyword_to_remove}' wilt verwijderen?", parent=self):
            categories = self.load_json(CATEGORIES_FILE)
            if keyword_to_remove in categories:
                del categories[keyword_to_remove]
                self.save_json(categories, CATEGORIES_FILE)
                self.load_categories()

    # --- Event Log Tab ---
    def create_event_log_tab(self):
        frame = self.tab_event_log
        self.log_refresh_interval = 5000 # Refresh log every 5 seconds (5000 ms)

        
        log_frame = ttk.LabelFrame(frame, text="Gebeurtenissenlogboek")
        log_frame.pack(padx=10, pady=10, fill='both', expand=True)

        cols = ('Timestamp', 'Type', 'Details')
        self.log_tree = ttk.Treeview(log_frame, columns=cols, show='headings')
        for col in cols:
            self.log_tree.heading(col, text=col)
        self.log_tree.pack(side='left', fill='both', expand=True)
        self.log_tree.tag_configure('new_entry', background='light yellow')

        scrollbar = ttk.Scrollbar(log_frame, orient='vertical', command=self.log_tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.log_tree.config(yscrollcommand=scrollbar.set)

        print(f"[{datetime.now()}] [GUI_LOG_LOAD] Initial call to load_event_log in create_event_log_tab.")
        self.load_event_log() # Initial load
        self.schedule_log_refresh() # Start auto-refresh

    def load_event_log(self):
        logging.debug(f"[{datetime.now()}] [GUI_LOG_LOAD] load_event_log called. Current Log Tree items: {len(self.log_tree.get_children())}, Last known GUI timestamp: {self.last_log_timestamp}")
        events_data = self.load_json(HFL_EVENTS_FILE)
        logging.debug(f"[{datetime.now()}] [GUI_LOG_LOAD_DATA] Raw events_data from {HFL_EVENTS_FILE}: {events_data}") # Log the raw data
        previous_latest_ts = self.last_log_timestamp

        # Clear existing entries
        for i in self.log_tree.get_children():
            self.log_tree.delete(i)

        events_list = events_data if isinstance(events_data, list) else []
        try:
            # Sort by timestamp: oldest to newest for the reversed loop later
            # Handles cases where timestamp might be missing or malformed by defaulting to empty string for sorting robustness
            events = sorted(events_list, key=lambda x: x.get('timestamp', ''))
            logging.debug(f"[{datetime.now()}] [GUI_LOG_LOAD] Successfully sorted {len(events)} events by timestamp.")
        except Exception as e_sort:
            logging.error(f"[{datetime.now()}] [GUI_LOG_LOAD_ERROR] Error sorting events: {e_sort}. Using unsorted.")
            events = events_list # Fallback to unsorted if error

        # Update the latest timestamp before inserting
        new_latest_timestamp_candidate = self.last_log_timestamp
        if events:
            # Assuming events are already sorted chronologically (oldest to newest) from JSON
            new_latest_timestamp_candidate = events[-1].get('timestamp', self.last_log_timestamp)

        logging.debug(f"[{datetime.now()}] [GUI_LOG_LOAD] Loaded {len(events)} events from {HFL_EVENTS_FILE}. Current self.last_log_timestamp: {self.last_log_timestamp}, New candidate: {new_latest_timestamp_candidate}")
        self.last_log_timestamp = new_latest_timestamp_candidate # Update after processing all current events
        # Display most recent events first
        for event in reversed(events):
            original_ts_str = event.get('timestamp', '')
            event_type = event.get('type', '')
            details = event.get('category', '') or event.get('entry', '')

            # Format timestamp for display
            try:
                dt_obj = datetime.fromisoformat(original_ts_str)
                display_ts = dt_obj.strftime('%d-%m %H:%M')
            except (ValueError, TypeError):
                display_ts = original_ts_str # Fallback

            # Determine if the entry is new
            tags = ()
            if previous_latest_ts and original_ts_str > previous_latest_ts:
                tags = ('new_entry',)

            self.log_tree.insert('', 'end', values=(display_ts, event_type, details), tags=tags)

    def schedule_log_refresh(self):
        # Schedule the next refresh of the event log
        if self.winfo_exists(): # Check if window/widget still valid
            try:
                if hasattr(self, 'log_refresh_id') and self.log_refresh_id:
                    self.after_cancel(self.log_refresh_id)
                self.log_refresh_id = self.after(self.log_refresh_interval, self.refresh_log_and_reschedule)
            except tk.TclError:
                logging.debug("TclError in schedule_log_refresh, window likely destroyed.")
            except AttributeError:
                logging.debug("AttributeError in schedule_log_refresh, likely during shutdown.")

    def refresh_log_and_reschedule(self):
        self.load_event_log()
        self.schedule_log_refresh() # Reschedule for the next update

    # --- Statistics Tab ---
    def create_statistics_tab(self):
        frame = self.tab_statistics

        if not MATPLOTLIB_AVAILABLE:
            ttk.Label(frame, text="Matplotlib is niet geïnstalleerd. Grafieken kunnen niet worden weergegeven.", foreground="red").pack(padx=10, pady=20)
            return

        # Create a sub-notebook for the graphs
        stats_notebook = ttk.Notebook(frame)
        stats_notebook.pack(expand=True, fill='both', padx=5, pady=5)

        # Create frames for each graph tab
        tab_cat_totals = ttk.Frame(stats_notebook)
        tab_daily_activity = ttk.Frame(stats_notebook)

        stats_notebook.add(tab_cat_totals, text="Totaal per Categorie")
        stats_notebook.add(tab_daily_activity, text="Items per Uur")

        # The existing graph frames will now be placed inside these new tabs
        self.cat_graph_frame = ttk.LabelFrame(tab_cat_totals, text="Totaal per Categorie (sinds start)")
        self.cat_graph_frame.pack(padx=10, pady=10, fill='both', expand=True)

        self.daily_graph_frame = ttk.LabelFrame(tab_daily_activity, text="Gemiddeld Items per Uur (Vandaag)")
        self.daily_graph_frame.pack(padx=10, pady=10, fill='both', expand=True)

        # Graphs will auto-refresh
        self.stats_refresh_interval = 5000 # 5 seconds

        # Initial call to load and display graphs and start the refresh cycle
        self.update_statistics_graphs()
        self.schedule_stats_refresh()

    def clear_frame(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()

    def update_statistics_graphs(self):
        if not MATPLOTLIB_AVAILABLE:
            return
        
        # Show loading message and start background thread for graph generation
        for frame in [self.cat_graph_frame, self.daily_graph_frame]:
            self.clear_frame(frame)
            ttk.Label(frame, text="Grafiek laden...").pack(pady=20)

        threading.Thread(target=self._generate_graphs_in_background, daemon=True).start()

    def _generate_graphs_in_background(self):
        # This runs in a background thread to avoid freezing the GUI
        cat_fig = None
        daily_fig = None
        total_items_count = 0
        error_occurred_cat = False
        error_occurred_daily = False

        try:
            cat_fig = self._prepare_category_plot()
        except Exception as e:
            logging.error(f"Error preparing category plot: {e}", exc_info=True)
            error_occurred_cat = True

        try:
            daily_fig, total_items_count = self._prepare_daily_plot()
        except Exception as e:
            logging.error(f"Error preparing daily plot: {e}", exc_info=True)
            error_occurred_daily = True

        # Schedule the GUI update back on the main thread
        if error_occurred_cat:
            self.after(0, self._embed_error_message, self.cat_graph_frame, "Fout bij laden categoriegrafiek.")
        else:
            self.after(0, self._embed_graph, self.cat_graph_frame, cat_fig)
            
        if error_occurred_daily:
            self.after(0, self._embed_error_message, self.daily_graph_frame, "Fout bij laden daggrafiek.")
        else:
            self.after(0, self._embed_graph, self.daily_graph_frame, daily_fig, total_items_count)

    def _embed_graph(self, frame, fig, total_items_value=None):
        # This runs on the main GUI thread
        self.clear_frame(frame)

        # Display total items label for the daily graph frame if value is available
        if frame == self.daily_graph_frame and total_items_value is not None:
            total_items_text = f"Totaal items vandaag: {total_items_value}"
            ttk.Label(frame, text=total_items_text).pack(pady=(5,0)) # Pack it first

        if fig is None:
            # If fig is None, the label (if applicable) is already packed.
            # Now add the "no data" message for the graph area.
            no_data_pady = 10 if (frame == self.daily_graph_frame and total_items_value is not None) else 20
            ttk.Label(frame, text="Nog geen data beschikbaar.").pack(pady=no_data_pady)
            return # No canvas to draw

        # If fig is not None, draw it
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        if frame == self.cat_graph_frame:
            if self.category_canvas and self.category_canvas.figure != fig:
                 plt.close(self.category_canvas.figure) # Close previous figure if different
            self.category_canvas = canvas
        elif frame == self.daily_graph_frame:
            if self.daily_canvas and self.daily_canvas.figure != fig:
                plt.close(self.daily_canvas.figure) # Close previous figure if different
            self.daily_canvas = canvas

    def _embed_error_message(self, frame, error_message):
        # This runs on the main GUI thread, called via self.after()
        self.clear_frame(frame)
        ttk.Label(frame, text=error_message, foreground="red").pack(pady=20)
        # Optionally, log this to the main application log as well if not already done
        logging.info(f"Displaying error in GUI frame '{frame}': {error_message}")

    def _prepare_category_plot(self):
        logging.info(f"[{datetime.now()}] [GUI_CAT_PLOT_FETCH] Calling get_runtime_category_totals()...")
        current_category_totals = get_runtime_category_totals()
        logging.info(f"[{datetime.now()}] [GUI_CAT_PLOT_FETCH_DATA] Received from HFL: {current_category_totals}")
        logging.info(f"[{datetime.now()}] [GUI_STATS_PLOT] Preparing category plot. Data: {current_category_totals}")

        if not current_category_totals:
            logging.info(f"[{datetime.now()}] [GUI_STATS_PLOT] No data for category plot.")
            return None # No data to plot

        fig = Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot(111)
        categories = list(current_category_totals.keys())
        counts = list(current_category_totals.values())
        ax.bar(categories, counts, color='cornflowerblue')
        ax.set_ylabel('Aantal Items')
        ax.set_title('Totaal per Categorie (sinds start)')
        fig.autofmt_xdate(rotation=45, ha='right') # Rotate labels for better readability
        fig.tight_layout() # Adjust layout to prevent labels from being cut off
        logging.info(f"[{datetime.now()}] [GUI_STATS_PLOT] Category plot figure prepared.")
        return fig

    def schedule_stats_refresh(self):
        if MATPLOTLIB_AVAILABLE and hasattr(self, 'stats_refresh_interval') and self.winfo_exists():
            try:
                if hasattr(self, 'stats_refresh_id') and self.stats_refresh_id:
                    self.after_cancel(self.stats_refresh_id)
                self.stats_refresh_id = self.after(self.stats_refresh_interval, self.refresh_stats_and_reschedule)
            except tk.TclError: # Occurs if window is destroyed
                logging.debug("TclError in schedule_stats_refresh, window likely destroyed.")
            except AttributeError:
                logging.debug("AttributeError in schedule_stats_refresh, likely during shutdown.")

    def refresh_stats_and_reschedule(self):
        if not self.winfo_exists(): # Stop if window is destroyed
            return
        self.update_statistics_graphs()
        self.schedule_stats_refresh() # Reschedule for the next update

    def _prepare_daily_plot(self):
        # Load events to get timestamps for today's items
        events_data = self.load_json(HFL_EVENTS_FILE)
        events_list = events_data if isinstance(events_data, list) else []

        today = date.today()
        
        # --- Count items for today ---
        todays_item_count = 0
        for event in events_list:
            ts_str = event.get('timestamp')
            if not ts_str:
                continue
            try:
                ts = datetime.fromisoformat(ts_str)
                if ts.date() == today and event.get('category'):
                    todays_item_count += 1
            except (ValueError, TypeError):
                continue

        # --- Calculate active hours for today ---
        # Per user feedback, a standard 8-hour workday is assumed if there is any activity.
        active_hours_today = 8.0 if todays_item_count > 0 else 0.0

        # --- Calculate average items per hour ---
        items_per_hour = 0.0
        if active_hours_today > 0:
            items_per_hour = todays_item_count / active_hours_today

        logging.info(f"[{datetime.now()}] [GUI_STATS_PLOT] Today's stats: Items={todays_item_count}, Active Hours={active_hours_today:.2f}, Items/Hour={items_per_hour:.2f}")

        if todays_item_count == 0:
            logging.info(f"[{datetime.now()}] [GUI_STATS_PLOT] No items for today, skipping plot.")
            return None, todays_item_count # Return 0 items

        # --- Prepare Plot (single bar for today's average) ---
        fig = Figure(figsize=(7, 5), dpi=100)
        ax = fig.add_subplot(111)

        day_names = {
            'Monday': 'Maandag',
            'Tuesday': 'Dinsdag',
            'Wednesday': 'Woensdag',
            'Thursday': 'Donderdag',
            'Friday': 'Vrijdag',
            'Saturday': 'Zaterdag',
            'Sunday': 'Zondag'
        }
        ax.bar([day_names[today.strftime('%A')]], [items_per_hour], color='mediumseagreen', width=0.4)
        ax.set_ylabel('Gemiddeld Items per Uur')
        ax.set_title('Gemiddeld Items per Uur (Vandaag)')

        # Display the value on top of the bar
        for bar in ax.patches:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f'{bar.get_height():.2f}',
                ha='center',
                va='bottom',
                fontsize=10
            )
        
        # Adjust y-axis to make small values more visible
        if items_per_hour > 0:
            ax.set_ylim(0, items_per_hour * 1.5)
        else:
            ax.set_ylim(0, 1) # Set a default limit if no items

        fig.tight_layout()
        
        logging.info(f"[{datetime.now()}] [GUI_STATS_PLOT] Daily average plot prepared.")
        
        # Return figure and total items for the label below the graph
        return fig, todays_item_count

if __name__ == '__main__':
    # This allows testing the GUI independently
    root = tk.Tk()
    root.withdraw() # Hide the root window
    app = SettingsWindow(root)
    app.mainloop()
