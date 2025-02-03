import os
from datetime import datetime
import subprocess
import threading
import logging
import queue
import tkinter as tk
from tkinter import ttk, filedialog

# ===================================================================== #
# Tooltip class
# ===================================================================== #
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window is not None:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tooltip_window, text=self.text, background="lightyellow", borderwidth=1, relief="solid")
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

# ===================================================================== #
# SubprocessRunner class
# ===================================================================== #
class SubprocessRunner:
    def __init__(self, root, output_path, cmd, type, name_prefix):
        self.root = root
        self.output_path = output_path
        self.cmd = cmd
        self.type = type
        self.name_prefix = name_prefix
        self.output_queue = queue.Queue()

    def run_subprocess(self):
        # Create a new Toplevel window
        self.popup = tk.Toplevel(self.root)
        self.popup.title(f"Running BETA-{self.type}")
        self.popup.geometry("800x600")

        # Create a Text widget to display output
        self.output_text = tk.Text(self.popup)
        self.output_text.pack(expand=True, fill='both')

        # Set up logging
        self.logger = logging.getLogger(f"BETA-{self.type}")
        self.logger.setLevel(logging.DEBUG)
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.file_handler = logging.FileHandler(f"{self.output_path}BETA-{self.type}-{'-'.join(self.name_prefix.get().split())}_{current_time}.log")
        self.formatter = logging.Formatter('%(levelname)s : %(name)s : %(message)s')
        self.file_handler.setFormatter(self.formatter)
        self.logger.addHandler(self.file_handler)

        
        def read_output(pipe, queue):
            for line in iter(pipe.readline, b''):
                if line.strip():  # Only process non-empty lines
                    queue.put(line)
            pipe.close()

        def update_output():
            try:
                while True:
                    try:
                        line = self.output_queue.get_nowait()
                        self.output_text.insert(tk.END, line)
                        self.output_text.see(tk.END)
                        self.output_text.update()
                        self.logger.info(line.strip())
                    except queue.Empty:
                        break
                self.popup.after(10, update_output)  # Check for new output every 10ms
            except tk.TclError:
                # Window has been closed
                pass
        

        def run_cmd():
            self.logger.info(f"Command: {self.cmd}")
            self.output_text.insert(tk.END, f"Command: {self.cmd}\n")
            self.process = subprocess.Popen(self.cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
            
            self.t = threading.Thread(target=read_output, args=(self.process.stdout, self.output_queue))
            self.t.daemon = True
            self.t.start()
            
            self.process.wait()
            self.output_queue.put("Process completed.\n")
        
        threading.Thread(target=run_cmd, daemon=True).start()
        self.popup.after(10, update_output)

# ===================================================================== #
# BetaFrame class
# ===================================================================== #
class BetaFrame(tk.Canvas):
    def __init__(self, notebook, type="plus", max_width=800):
        super().__init__()
        self.notebook = notebook
        self.max_width = max_width
        self.num_widgets = 0
        self.type = type
        self.output_path = "./"

        self.style = ttk.Style()
        self.style.theme_use('alt')
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.yview)
        self.scrollable_frame = ttk.Frame(self)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.configure(
                scrollregion=self.bbox("all")
            )
        )
        self.create_window((0, 0), window=self.scrollable_frame, anchor="w")
        self.configure(yscrollcommand=self.scrollbar.set)
        self.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
    def add_description(self, text):
        self.description = tk.Label(self.scrollable_frame, text=text, justify="left", wraplength=self.max_width, font=('Arial', 12, 'bold'))
        self.description.grid(row=self.num_widgets, columnspan=2, padx=10, pady=10, sticky='NSEW')
        self.num_widgets += 1

    def add_cmd(self, cmd):
        '''
        label = tk.Label(self.scrollable_frame, text="Command to be executed:", justify="left", font=('Arial', 10), wraplength=self.max_width//2)
        label.grid(row=self.num_widgets, column=0, padx=10, sticky='E')
        self.cmd = tk.Label(self.scrollable_frame, text=cmd, font=('Arial', 10, 'bold'), wraplength=self.max_width//2, justify="left")
        self.cmd.grid(row=self.num_widgets, column=1, padx=10, pady=10, sticky='W')
        self.num_widgets += 1
        '''
        self.cmd = tk.StringVar()

    def update_cmd(self):
        command_text = f"BETA {self.type}"
        if self.genome.get():
            if self.genome.get() != 'Other':
                command_text += f" -g {self.genome.get()}"
            else:
                if self.reference_file_path != "":
                    command_text += f" -r {self.reference_file_path}"
        if self.bl_state.get():
            command_text += " --bl"
        if self.peak_number.get():
            command_text += f" --pn {self.peak_number.get()}"
        if self.distance.get():
            command_text += f" -d {self.distance.get()}"
        if self.output_path:
            command_text += f" -o {self.output_path}"
        if self.name_prefix and self.name_prefix.get() != "":
            command_text += f" -n {'-'.join(self.name_prefix.get().split())}"
        else:
            command_text = command_text.replace(f" -n {self.name_prefix.get()}", "")
        if self.boundary_file_path:
            command_text += f" --bf {self.boundary_file_path}"
        if self.type != 'minus':
            if self.gname_state.get():
                command_text += " --gname2"
            if self.expression_file_path:
                command_text += f" -e {self.expression_file_path}"
            if self.kind.get():
                command_text += f" -k {self.kind_options[self.kind.get()]}"
            if self.kind_info_id.get() and self.kind_info_change.get() and self.kind_info_stat.get():
                command_text += f" --info {self.kind_info_id.get()},{self.kind_info_change.get()},{self.kind_info_stat.get()}"
            if self.method.get():
                command_text += f" --method {self.method.get()}"
            if self.fdr.get():
                command_text += f" --df {self.fdr.get()}"
            if self.gene_amount.get():
                command_text += f" --da {self.gene_amount.get()}"
            if self.pvalue_cutoff.get():
                command_text += f" -c {self.pvalue_cutoff.get()}"
            if self.type != 'basic':
                if self.genome_sequence_file_path:
                    command_text += f" --gs {self.genome_sequence_file_path}"
                if self.number_motifs.get():
                    command_text += f" --mn {self.number_motifs.get()}"
        if self.peaks_file_path:
            command_text += f" -p {self.peaks_file_path}"
        
        #self.cmd.config(text=command_text)
        self.cmd = command_text

    def add_label(self, text, font=('Arial', 10), colspan=1, column=0, padx=10, pady=10, sticky='NSEW'):
        label = tk.Label(self.scrollable_frame, text=text, justify="left", font=font, wraplength=self.max_width)
        label.grid(row=self.num_widgets, columnspan=colspan, column=column, padx=padx, pady=pady, sticky=sticky)
        self.num_widgets += 1

    def add_text(self, text, font=('Arial', 10), width=80, height=1, colspan=1, column=0, padx=10, pady=10, sticky='NSEW'):
        txt = tk.Text(self.scrollable_frame, width=width, height=height, wrap=tk.WORD, bg=self.cget("bg"), bd=0, highlightthickness=0, font=font)
        txt.insert(tk.END, text)
        txt.config(state="disabled") 
        txt.grid(row=self.num_widgets, columnspan=colspan, column=column, padx=padx, pady=pady, sticky=sticky)
        self.num_widgets += 1

    def add_expression_file_button(self):
        self.expression_file_path = ""
        self.expression_label = tk.Label(self.scrollable_frame, text="No expression file selected.", wraplength=self.max_width//2)
        self.expression_label.grid(row=self.num_widgets, column=1, pady=5, sticky='W')

        self.expression_button = tk.Button(self.scrollable_frame, text="Browse expression files", command=self.select_expression_file)
        self.expression_button.grid(row=self.num_widgets, column=0, pady=5, padx=10, sticky='E')
        ToolTip(self.expression_button, "Select a tab-delimited expression file (with no header).")
        self.num_widgets += 1

    def select_expression_file(self):
        self.expression_file_path = filedialog.askopenfilename(
            title="Select Expression File",
            initialdir="./",
            filetypes=(("Tab-delimited", "*.tsv"),
                    ("All files", "*.*"))
        )
        if self.expression_file_path:
            self.expression_label.config(text=f"Expression file:\n{os.path.basename(self.expression_file_path)}")
        else:
            self.expression_file_path = ""
            self.expression_label.config(text="No expression file selected.")
        self.validate_run_params()
        self.update_cmd()

    def add_peaks_file_button(self):
        self.peaks_file_path = ""
        self.peaks_label = tk.Label(self.scrollable_frame, text="No peaks file selected.", wraplength=self.max_width//2)
        self.peaks_label.grid(row=self.num_widgets, column=1, pady=5, sticky='W')
        self.peaks_button = tk.Button(self.scrollable_frame, text="Browse peak files", command=self.select_peaks_file)
        self.peaks_button.grid(row=self.num_widgets, column=0, pady=5, padx=10, sticky='E')
        ToolTip(self.peaks_button, "The bed format of peaks binding sites (with no header).\n(BETA support 3 or 5 columns bed format, CHROM, START, END (NAME, SCORE)")
        self.num_widgets += 1

    def select_peaks_file(self):
        self.peaks_file_path = filedialog.askopenfilename(
            title="Select Peaks File",
            initialdir="./", 
            filetypes=(("Bed", "*.bed"),
                    ("NarrowPeak", "*.narrowPeak"),
                    ("BroadPeak", "*.broadPeak"),
                    ("All files", "*.*"))
        )
        if self.peaks_file_path:
            self.peaks_label.config(text=f"Peaks file:\n{os.path.basename(self.peaks_file_path)}")
        else:
            self.peaks_file_path = ""
            self.peaks_label.config(text="No peaks file selected.")
        self.validate_run_params()
        self.update_cmd()

    def add_boundary_file_button(self):
        self.boundary_file_path = ""
        self.boundary_label = tk.Label(self.scrollable_frame, text="No CTCF boundary file selected.", wraplength=self.max_width//2)
        self.boundary_label.grid(row=self.num_widgets, column=1, pady=5, sticky='W')
        self.boundary_button = tk.Button(self.scrollable_frame, text="Browse CTCF boundary files", command=self.select_boundary_file, state=tk.DISABLED)
        self.boundary_button.grid(row=self.num_widgets, column=0, pady=5, padx=10, sticky='E')
        ToolTip(self.boundary_button, "CTCF conserved peaks bed file.\nUse this only when you set boundary limit and the genome is neither hg19 nor mm9.")
        self.num_widgets += 1

    def select_boundary_file(self):
        self.boundary_file_path = filedialog.askopenfilename(
            title="Select CTCF Boundary File",
            initialdir="./", 
            filetypes=(("Bed", "*.bed"),
                    ("All files", "*.*"))
        )
        if self.boundary_file_path:
            self.boundary_label.config(text=f"CTCF file: {os.path.basename(self.boundary_file_path)}")
        else:
            self.boundary_file_path = ""
            self.boundary_label.config(text="No CTCF boundary file selected.")
        
        self.update_cmd()
    
    def add_reference_file_button(self):
        self.reference_file_path = ""
        self.reference_label = tk.Label(self.scrollable_frame, text="No reference genome file selected.\n(Required only if genome is Other).", wraplength=self.max_width//2)
        self.reference_label.grid(row=self.num_widgets, column=1, pady=5, sticky='W')
        self.reference_button = tk.Button(self.scrollable_frame, text="Browse reference genome files", command=self.select_reference_file, state=tk.NORMAL)
        self.reference_button.grid(row=self.num_widgets, column=0, pady=5, padx=10, sticky='E')
        ToolTip(self.reference_button, "RefGene info file downloaded from UCSC genome browser.\nInput this file only if your genome is neither hg18, hg19, hg38, mm9, or mm10.")
        self.num_widgets += 1

    def select_reference_file(self):
        self.reference_file_path = filedialog.askopenfilename(
            title="Select Reference Genome File",
            initialdir="./", 
            filetypes=(("GTF", "*.gtf"),
                       ("Text", "*.txt"),
                       ("Fasta", "*.fa"),
                       ("Tab-delimited", "*.tsv"),
                       ("Comma-separated", "*.csv"),
                    ("All files", "*.*"))
        )
        if self.reference_file_path:
            self.reference_label.config(text=f"Reference Genome file: {os.path.basename(self.reference_file_path)}")
        else:
            self.reference_file_path = ""
            self.reference_label.config(text="No reference file selected.\n(Required only if genome is Other).")
        self.validate_run_params()
        self.update_cmd()

    def update_genome(self, event):
        if self.genome.get() != 'mm9' and self.genome.get() != 'hg19' and self.bl_state.get() == True:
            self.boundary_button.config(state=tk.NORMAL)
        else:
            self.boundary_button.config(state=tk.DISABLED)
            self.boundary_file_path = ""
            self.boundary_label.config(text="No CTCF boundary file selected.")
        if self.genome.get() == 'Other':
            self.reference_button.config(state=tk.NORMAL)
        else:
            self.reference_file_path = ""
            self.reference_button.config(state=tk.DISABLED)
            self.reference_label.config(text="No reference genome file selected.\n(Required only if genome is Other).")

        self.validate_run_params()
        self.update_cmd()

    def add_genome_dropdown(self, genome_options=["Other", "hg38", "hg19", "hg18", "mm10", "mm9"]):
        self.genome_options = genome_options
        self.genome = tk.StringVar()
        self.genome.set("Other")
        self.genome_label = tk.Label(self.scrollable_frame, text=f"Reference genome:", wraplength=self.max_width//2)
        self.genome_label.grid(row=self.num_widgets, column=0, pady=5, padx=10, sticky='E')
        self.genome_dropdown = tk.OptionMenu(self.scrollable_frame, self.genome, *self.genome_options, command=self.update_genome)
        self.genome_dropdown.grid(row=self.num_widgets, column=1, pady=5, padx=10, sticky='W')
        ToolTip(self.genome_dropdown, "Select the reference genome.")
        self.num_widgets += 1

    def update_kind_info_id(self, *args):
        if self.kind_info_id.get():
            self.update_cmd()

    def add_info_id_textbox(self):
        # variable for gene id column
        self.kind_info_id_defaults = {"DESeq2": 1, "Limma": 1, "EdgeR": 1, "Cuffdiff": 2, "BETA-Specific Format": 1, "Other": 1}
        self.validate_command_info_id = self.register(self.validate_integer_input)
        self.kind_info_id = tk.StringVar()
        self.kind_info_id.set(self.kind_info_id_defaults[self.kind.get()])

        self.kind_info_id_label = tk.Label(self.scrollable_frame, text="Column of gene IDs:", wraplength=self.max_width//2)
        self.kind_info_id_label.grid(row=self.num_widgets, column=0, pady=5, padx=10, sticky='E')
        self.kind_info_id.trace_add("write", self.update_kind_info_id)

        self.kind_info_id_entry = tk.Entry(self.scrollable_frame, textvariable=self.kind_info_id, validate="key", validatecommand=(self.validate_command_info_id, '%P'))
        self.kind_info_id_entry.place(width=50)
        self.kind_info_id_entry.grid(row=self.num_widgets, column=1, pady=5, sticky='W')
        ToolTip(self.kind_info_id_label, "Column number in the expression file designated as the gene ID (starting from 1).")
        self.num_widgets += 1

    def update_kind_info_change(self, *args):
        if self.kind_info_change.get():
            self.update_cmd()

    def add_info_change_textbox(self):
        # variable for differential change column
        self.kind_info_change_defaults = {"DESeq2": 3, "Limma": 2, "EdgeR": 2, "Cuffdiff": 10, "BETA-Specific Format": 2, "Other": 2}
        self.validate_command_info_change = self.register(self.validate_integer_input)
        self.kind_info_change = tk.StringVar()
        self.kind_info_change.set(self.kind_info_change_defaults[self.kind.get()])

        self.kind_info_change_label = tk.Label(self.scrollable_frame, text="Column of logFC:", wraplength=self.max_width//2)
        self.kind_info_change_label.grid(row=self.num_widgets, column=0, pady=5, padx=10, sticky='E')
        self.kind_info_change.trace_add("write", self.update_kind_info_change)

        self.kind_info_change_entry = tk.Entry(self.scrollable_frame, textvariable=self.kind_info_change, validate="key", validatecommand=(self.validate_command_info_change, '%P'))
        self.kind_info_change_entry.place(width=50)
        self.kind_info_change_entry.grid(row=self.num_widgets, column=1, pady=5, sticky='W')
        ToolTip(self.kind_info_change_label, "Column number in the expression file designated as metric for magnitude of change (starting from 1).")
        self.num_widgets += 1

    def update_kind_info_stat(self, *args):
        if self.kind_info_stat.get():
            self.update_cmd()

    def add_info_stat_textbox(self):
        # variable for differential change column
        self.kind_info_stat_defaults = {"DESeq2": 7, "Limma": 6, "EdgeR": 5, "Cuffdiff": 13, "BETA-Specific Format": 3, "Other": 3}
        self.validate_command_info_stat = self.register(self.validate_integer_input)
        self.kind_info_stat = tk.StringVar()
        self.kind_info_stat.set(self.kind_info_stat_defaults[self.kind.get()])

        self.kind_info_stat_label = tk.Label(self.scrollable_frame, text="Column of FDR:", wraplength=self.max_width//2)
        self.kind_info_stat_label.grid(row=self.num_widgets, column=0, pady=5, padx=10, sticky='E')
        self.kind_info_stat.trace_add("write", self.update_kind_info_stat)

        self.kind_info_stat_entry = tk.Entry(self.scrollable_frame, textvariable=self.kind_info_stat, validate="key", validatecommand=(self.validate_command_info_stat, '%P'))
        self.kind_info_stat_entry.place(width=50)
        self.kind_info_stat_entry.grid(row=self.num_widgets, column=1, pady=5, sticky='W')
        ToolTip(self.kind_info_stat_label, "Column number in the expression file designated as the statistical significance (starting from 1).")
        self.num_widgets += 1

    def update_kind(self, event):
        self.kind_info_id.set(self.kind_info_id_defaults[self.kind.get()])
        self.kind_info_change.set(self.kind_info_change_defaults[self.kind.get()])
        self.kind_info_stat.set(self.kind_info_stat_defaults[self.kind.get()])
        self.validate_run_params()
        self.update_cmd()

    def add_kind_dropdown(self, kind_options={"DESeq2": "O", "Limma": "LIM", "EdgeR": "O", "Cuffdiff": "CUF", "BETA-Specific Format": "BSF", "Other": "O"}):
        self.kind_options = kind_options
        self.kind = tk.StringVar()
        self.kind.set("DESeq2")
        self.kind_label = tk.Label(self.scrollable_frame, text=f"Kind of expression file:", wraplength=self.max_width//2)
        self.kind_label.grid(row=self.num_widgets, column=0, pady=5, padx=10, sticky='E')
        self.kind_dropdown = tk.OptionMenu(self.scrollable_frame, self.kind, *self.kind_options, command=self.update_kind)
        self.kind_dropdown.grid(row=self.num_widgets, column=1, pady=5, padx=10, sticky='W')
        ToolTip(self.kind_dropdown, "Select the kind of expression file.")
        self.num_widgets += 1

    def update_method(self, event):
        self.validate_run_params()
        self.update_cmd()

    def add_method_dropdown(self, method_options=['score', 'distance']):
        self.method_options = method_options
        self.method = tk.StringVar()
        self.method.set("score")
        self.method_label = tk.Label(self.scrollable_frame, text=f"Method for TF/CR function prediction:", wraplength=self.max_width//2)
        self.method_label.grid(row=self.num_widgets, column=0, pady=5, padx=10, sticky='E')
        self.method_dropdown = tk.OptionMenu(self.scrollable_frame, self.method, *self.method_options, command=self.update_method)
        self.method_dropdown.grid(row=self.num_widgets, column=1, pady=5, padx=10, sticky='W')
        ToolTip(self.method_dropdown, "Define method for TF/CR function prediction.\nscore for regulatory potential, distance for the distance to the proximal binding peak.")
        self.num_widgets += 1

    def add_gname_checkbox(self):
        self.gname_state = tk.BooleanVar()
        self.gname_checkbutton = tk.Checkbutton(self.scrollable_frame, text="IDs are gene symbols", variable=self.gname_state, command=self.update_cmd)
        self.gname_checkbutton.grid(row=self.num_widgets, column=0, columnspan=2, pady=5, padx=10, sticky='NSEW')
        ToolTip(self.gname_checkbutton, "Gene/transcript IDs in expression file will be considered as official gene symbols.")
        self.num_widgets += 1
    
    def update_bl_checkbox(self):
        if self.genome.get() != 'mm9' and self.genome.get() != 'hg19' and self.bl_state.get() == True:
            self.boundary_button.config(state=tk.NORMAL)
        else:
            self.boundary_button.config(state=tk.DISABLED)
            self.boundary_file_path = ""
            self.boundary_label.config(text="No CTCF boundary file selected.")
        self.update_cmd()

    def add_bl_checkbox(self):
        self.bl_state = tk.BooleanVar()
        self.bl_checkbutton = tk.Checkbutton(self.scrollable_frame, text="CTCF boundary limit", variable=self.bl_state, command=self.update_bl_checkbox)
        self.bl_checkbutton.grid(row=self.num_widgets, column=0, columnspan=2, pady=5, padx=10, sticky='NSEW')
        ToolTip(self.bl_checkbutton, "Use CTCF boundary to get a peak’s associated gene.")
        self.num_widgets += 1

    def select_output_folder(self):
        self.output_path=filedialog.askdirectory(
            title="Select output directory",
            initialdir="./"
        )
        if self.output_path != "./":
            self.output_path += '/'
            self.output_label.config(text=f"Output directory: {os.path.basename(self.output_path[:-1])}/")
        else:
            self.output_path="./"
            self.output_label.config(text="Output directory: ./")
            
        self.update_cmd()

    def add_output_folder_button(self):
        self.output_label = tk.Label(self.scrollable_frame, text="Output directory: ./", wraplength=self.max_width//2)
        self.output_label.grid(row=self.num_widgets, column=1, pady=5, sticky='W')
        self.output_button = tk.Button(self.scrollable_frame, text="Browse output directories", command=self.select_output_folder)
        self.output_button.grid(row=self.num_widgets, column=0, pady=5, padx=10, sticky='E')
        ToolTip(self.output_button, "Directory to store all BETA analysis output files.")
        self.num_widgets += 1

    def update_name_prefix(self, *args):
        if self.name_prefix:
            self.update_cmd()

    def add_name_prefix_textbox(self):
        self.name_prefix = tk.StringVar()
        self.name_prefix_label = tk.Label(self.scrollable_frame, text="Prefix for output files:", wraplength=self.max_width//2)
        self.name_prefix_label.grid(row=self.num_widgets, column=0, pady=5, padx=10, sticky='E')
        self.name_prefix.trace_add("write", self.update_name_prefix)
        self.name_prefix_entry = tk.Entry(self.scrollable_frame, textvariable=self.name_prefix)
        self.name_prefix_entry.place(width=100)
        self.name_prefix_entry.grid(row=self.num_widgets, column=1, pady=5, sticky='W')
        ToolTip(self.name_prefix_label, "Used as prefix of the result file.\nIf not set, 'NA' will be used instead")
        self.num_widgets += 1

    def validate_integer_input(self, new_value):
        if new_value == "" or new_value.isdigit():  # Allow empty input (for deletion) or digits
            return True
        return False
    
    def validate_number(self, val):
        if val == "":
            return True
        try:
            float(val)
            return True
        except ValueError:
            return False

    def update_peak_number(self, *args):
        if self.peak_number:
            self.update_cmd()

    def add_peak_number_textbox(self):
        self.validate_command_peaks = self.register(self.validate_integer_input)
        self.peak_number = tk.StringVar()
        self.peak_number.set(10000)
        self.peak_number_label = tk.Label(self.scrollable_frame, text="Number of peaks:", wraplength=self.max_width//2)
        self.peak_number_label.grid(row=self.num_widgets, column=0, pady=5, padx=10, sticky='E')
        self.peak_number.trace_add("write", self.update_peak_number)
        self.peak_number_entry = tk.Entry(self.scrollable_frame, textvariable=self.peak_number, validate="key", validatecommand=(self.validate_command_peaks, '%P'))
        self.peak_number_entry.place(width=100)
        self.peak_number_entry.grid(row=self.num_widgets, column=1, pady=5, sticky='W')
        ToolTip(self.peak_number_label, "The number of peaks you want to consider.")
        self.num_widgets += 1

    def update_distance(self, *args):
        if self.distance:
            self.update_cmd()

    def add_distance_textbox(self):
        self.validate_command_distance = self.register(self.validate_integer_input)
        self.distance = tk.StringVar()
        self.distance.set(100000)
        self.distance_label = tk.Label(self.scrollable_frame, text="Distance of peaks to TSS (bp):", wraplength=self.max_width//2)
        self.distance_label.grid(row=self.num_widgets, column=0, pady=5, padx=10, sticky='E')
        self.distance.trace_add("write", self.update_distance)
        self.distance_entry = tk.Entry(self.scrollable_frame, textvariable=self.distance, validate="key", validatecommand=(self.validate_command_distance, '%P'))
        self.distance_entry.place(width=100)
        self.distance_entry.grid(row=self.num_widgets, column=1, pady=5, sticky='W')
        ToolTip(self.distance_label, "Get peaks within this distance from gene TSS.")
        self.num_widgets += 1

    def update_fdr(self, *args):
        if self.fdr:
            self.update_cmd()

    def add_fdr_textbox(self):
        self.validate_command_fdr = self.register(self.validate_number)
        self.fdr = tk.StringVar()
        self.fdr.set(1)
        self.fdr_label = tk.Label(self.scrollable_frame, text="FDR threshold:", wraplength=self.max_width//2)
        self.fdr_label.grid(row=self.num_widgets, column=0, pady=5, padx=10, sticky='E')
        self.fdr.trace_add("write", self.update_fdr)
        self.fdr_entry = tk.Entry(self.scrollable_frame, textvariable=self.fdr, validate="key", validatecommand=(self.validate_command_fdr, '%P'))
        self.fdr_entry.place(width=100)
        self.fdr_entry.grid(row=self.num_widgets, column=1, pady=5, sticky='W')
        ToolTip(self.fdr_label, "False discovery rate threshold to pick out from differential expressed genes (number from 0 to 1).")
        self.num_widgets += 1

    def update_gene_amount(self, *args):
        if self.gene_amount:
            self.update_cmd()

    def add_gene_amount_textbox(self):
        self.validate_command_genes = self.register(self.validate_number)
        self.gene_amount = tk.StringVar()
        self.gene_amount.set(0.5)
        self.gene_amount_label = tk.Label(self.scrollable_frame, text="Number or percent of genes:", wraplength=self.max_width//2)
        self.gene_amount_label.grid(row=self.num_widgets, column=0, pady=5, padx=10, sticky='E')
        self.gene_amount.trace_add("write", self.update_gene_amount)
        self.gene_amount_entry = tk.Entry(self.scrollable_frame, textvariable=self.gene_amount, validate="key", validatecommand=(self.validate_command_genes, '%P'))
        self.gene_amount_entry.place(width=100)
        self.gene_amount_entry.grid(row=self.num_widgets, column=1, pady=5, sticky='W')
        ToolTip(self.gene_amount_label, "Number (>1) or percentage (0-1).\nIf you want to use FDR, set this to 1, otherwise it uses the intersection of these two parameters.")
        self.num_widgets += 1

    def update_pvalue_cutoff(self, *args):
        if self.pvalue_cutoff:
            self.update_cmd()

    def add_pvalue_cutoff_textbox(self):
        self.validate_command_pvalue = self.register(self.validate_number)
        self.pvalue_cutoff = tk.StringVar()
        self.pvalue_cutoff.set(0.001)
        self.pvalue_cutoff_label = tk.Label(self.scrollable_frame, text="P-value cutoff for results:", wraplength=self.max_width//2)
        self.pvalue_cutoff_label.grid(row=self.num_widgets, column=0, pady=5, padx=10, sticky='E')
        self.pvalue_cutoff.trace_add("write", self.update_pvalue_cutoff)
        self.pvalue_cutoff_entry = tk.Entry(self.scrollable_frame, textvariable=self.pvalue_cutoff, validate="key", validatecommand=(self.validate_command_pvalue, '%P'))
        self.pvalue_cutoff_entry.place(width=100)
        self.pvalue_cutoff_entry.grid(row=self.num_widgets, column=1, pady=5, sticky='W')
        ToolTip(self.pvalue_cutoff_label, "Number (0-1) as threshold to select the target gene list(up regulated or down regulated or both) with p value called by one side ks-test")
        self.num_widgets += 1

    def add_genome_sequence_file_button(self):
        self.genome_sequence_file_path = ""
        self.genome_sequence_label = tk.Label(self.scrollable_frame, text="No genome sequence file selected.", wraplength=self.max_width//2)
        self.genome_sequence_label.grid(row=self.num_widgets, column=1, pady=5, sticky='W')
        self.genome_sequence_button = tk.Button(self.scrollable_frame, text="Browse genome sequence files", command=self.select_genome_sequence_file, state=tk.NORMAL)
        self.genome_sequence_button.grid(row=self.num_widgets, column=0, pady=5, padx=10, sticky='E')
        ToolTip(self.genome_sequence_button, "Genome sequence file in fasta format, used for motif analysis.")
        self.num_widgets += 1

    def select_genome_sequence_file(self):
        self.genome_sequence_file_path = filedialog.askopenfilename(
            title="Select Genome Sequence File",
            initialdir="./", 
            filetypes=(("Fasta", "*.fa"),
                       ("Fasta", "*.fasta"),
                    ("All files", "*.*"))
        )
        if self.genome_sequence_file_path:
            self.genome_sequence_label.config(text=f"Genome sequence file: {os.path.basename(self.genome_sequence_file_path)}")
        else:
            self.genome_sequence_file_path = ""
            self.genome_sequence_label.config(text="No genome sequence file selected.")
        self.validate_run_params()
        self.update_cmd()

    def update_number_motifs(self, *args):
        if self.number_motifs:
            self.update_cmd()

    def add_number_motifs_textbox(self):
        self.validate_command_motifs = self.register(self.validate_number)
        self.number_motifs = tk.StringVar()
        self.number_motifs.set(10)
        self.number_motifs_label = tk.Label(self.scrollable_frame, text="Number or p-value cutoff for motif results:", wraplength=self.max_width//2)
        self.number_motifs_label.grid(row=self.num_widgets, column=0, pady=5, padx=10, sticky='E')
        self.number_motifs.trace_add("write", self.update_number_motifs)
        self.number_motifs_entry = tk.Entry(self.scrollable_frame, textvariable=self.number_motifs, validate="key", validatecommand=(self.validate_command_motifs, '%P'))
        self.number_motifs_entry.place(width=100)
        self.number_motifs_entry.grid(row=self.num_widgets, column=1, pady=5, sticky='W')
        ToolTip(self.number_motifs_label, "Number of motifs (>1) or p-value cutoff (0-1) to retrieve motifs.")
        self.num_widgets += 1

    def validate_run_params(self):
        if self.genome.get() != "Other":
            if self.peaks_file_path != "":
                if self.type != 'minus':
                    if self.expression_file_path != '':
                        if self.type != 'basic':
                            if self.genome_sequence_file_path != '':
                                self.run_button.config(state=tk.NORMAL)
                        else:
                            self.run_button.config(state=tk.NORMAL)
                    else:
                        self.run_button.config(state=tk.DISABLED)
                else:
                    self.run_button.config(state=tk.NORMAL)
            else:
                self.run_button.config(state=tk.DISABLED)
        else:
            if self.reference_file_path != "":
                if self.peaks_file_path != "":
                    if self.type != 'minus':
                        if self.type != 'basic':
                            if self.genome_sequence_file_path != '':
                                self.run_button.config(state=tk.NORMAL)
                        else:
                            self.run_button.config(state=tk.NORMAL)
                    else:
                        self.run_button.config(state=tk.NORMAL)
                else:
                    self.run_button.config(state=tk.DISABLED)
            else:
                self.run_button.config(state=tk.DISABLED)

    def run_beta(self):
        #runner = SubprocessRunner(self, self.output_path, self.cmd.cget('text'), self.type, self.name_prefix)
        runner = SubprocessRunner(self, self.output_path, self.cmd, self.type, self.name_prefix)
        runner.run_subprocess()
        
    def add_run_button(self, text):
        self.run_button = tk.Button(self.scrollable_frame, text=text, font=('Arial', 12, 'bold'), command=self.run_beta, state=tk.DISABLED)
        self.run_button.grid(row=self.num_widgets, columnspan=2, pady=5)
        self.num_widgets += 1

    def add_reset_button(self):
        self.reset_button = tk.Button(self.scrollable_frame, text="Reset to Default", font=('Arial',12), command=self.reset_default)
        self.reset_button.grid(row=self.num_widgets, columnspan=2, pady=5)
        self.num_widgets += 1

    def reset_default(self):
        if self.type != 'minus':
            self.expression_file_path = ""
            self.expression_label.config(text="No expression file selected.")
            self.kind.set("DESeq2")
            self.kind_info_id.set(self.kind_info_id_defaults[self.kind.get()])
            self.kind_info_change.set(self.kind_info_change_defaults[self.kind.get()])
            self.kind_info_stat.set(self.kind_info_stat_defaults[self.kind.get()])
            self.method.set("score")
            self.peaks_file_path = ""
            self.peaks_label.config(text="No peaks file selected.")
            self.boundary_file_path = ""
            self.boundary_label.config(text="No CTCF boundary file selected.")
            self.genome.set("Other")
            self.reference_button.config(state=tk.NORMAL)
            self.reference_file_path = ""
            self.reference_label.config(text="No reference genome file selected.\n(Required only if genome is Other).")
            self.gname_state.set(False)
            self.bl_state.set(False)
            self.peak_number.set(10000)
            self.distance.set(100000)
            self.name_prefix.set("")
            self.output_path = "./"
            self.fdr.set(1)
            self.gene_amount.set(0.5)
            self.pvalue_cutoff.set(0.001)
            if self.type != 'basic':
                self.number_motifs.set(10)
                self.genome_sequence_file_path = ""
                self.reference_label.config(text="No genome sequence file selected.")
            self.run_button.config(state=tk.DISABLED)
        else:
            self.peaks_file_path = ""
            self.peaks_label.config(text="No peaks file selected.")
            self.boundary_file_path = ""
            self.boundary_label.config(text="No CTCF boundary file selected.")
            self.genome.set("Other")
            self.reference_button.config(state=tk.NORMAL)
            self.reference_file_path = ""
            self.reference_label.config(text="No reference genome file selected.\n(Required only if genome is Other).")
            self.bl_state.set(False)
            self.peak_number.set(10000)
            self.distance.set(100000)
            self.name_prefix.set("")
            self.output_path = "./"
            self.run_button.config(state=tk.DISABLED)
        
        
        self.update_cmd()

if __name__ == '__main__':
    # ===================================================================== #
    # Initialize the main window
    # ===================================================================== #
    root = tk.Tk()
    root.title("BETA")
    root.geometry("750x1100")
    root.minsize(width=750, height=700)

    # Create a notebook (tabbed interface)
    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True)

    # Create BETA plus frame
    beta_plus = BetaFrame(notebook, type="plus", max_width=800)
    notebook.add(beta_plus, text="BETA Plus")

    beta_plus.add_description("Predict direct targets of TF and the active/repressive function prediction.\nDo motif analysis at targets region as well.")
    beta_plus.add_cmd("BETA plus --pn 10000 -d 100000 -o ./ -k O --info 1,3,7 --method score --df 1 --da 0.5 -c 0.001 --mn 10")
    beta_plus.add_label("--------- REQUIRED PARAMETERS ---------", font=('Arial', 10, 'bold'), colspan=2)
    beta_plus.add_expression_file_button()
    beta_plus.add_kind_dropdown()
    beta_plus.add_info_id_textbox()
    beta_plus.add_info_change_textbox()
    beta_plus.add_info_stat_textbox()
    beta_plus.add_fdr_textbox()
    beta_plus.add_gene_amount_textbox()
    beta_plus.add_peaks_file_button()
    beta_plus.add_genome_dropdown()
    beta_plus.add_reference_file_button()
    beta_plus.add_method_dropdown()
    beta_plus.add_pvalue_cutoff_textbox()
    beta_plus.add_genome_sequence_file_button()
    beta_plus.add_number_motifs_textbox()
    beta_plus.add_label("--------- OPTIONAL PARAMTERS ---------", font=('Arial', 10, 'bold'), colspan=2)
    beta_plus.add_gname_checkbox()
    beta_plus.add_bl_checkbox()
    beta_plus.add_boundary_file_button()
    beta_plus.add_peak_number_textbox()
    beta_plus.add_distance_textbox()
    beta_plus.add_name_prefix_textbox()
    beta_plus.add_output_folder_button()
    beta_plus.add_run_button("Run BETA Plus")
    beta_plus.add_reset_button()

    # Create BETA basic frame
    beta_basic = BetaFrame(notebook, type="basic", max_width=750)
    notebook.add(beta_basic, text="BETA Basic")

    beta_basic.add_description("Predict direct targets of TF and the active/repressive function prediction.")
    beta_basic.add_cmd("BETA basic --pn 10000 -d 100000 -o ./ -k O --info 1,3,7 --method score --df 1 --da 0.5 -c 0.001")
    beta_basic.add_label("--------- REQUIRED PARAMETERS ---------", font=('Arial', 10, 'bold'), colspan=2)
    beta_basic.add_expression_file_button()
    beta_basic.add_kind_dropdown()
    beta_basic.add_info_id_textbox()
    beta_basic.add_info_change_textbox()
    beta_basic.add_info_stat_textbox()
    beta_basic.add_fdr_textbox()
    beta_basic.add_gene_amount_textbox()
    beta_basic.add_peaks_file_button()
    beta_basic.add_genome_dropdown()
    beta_basic.add_reference_file_button()
    beta_basic.add_method_dropdown()
    beta_basic.add_pvalue_cutoff_textbox()
    beta_basic.add_label("--------- OPTIONAL PARAMETERS ---------", font=('Arial', 10, 'bold'), colspan=2)
    beta_basic.add_gname_checkbox()
    beta_basic.add_bl_checkbox()
    beta_basic.add_boundary_file_button()
    beta_basic.add_peak_number_textbox()
    beta_basic.add_distance_textbox()
    beta_basic.add_name_prefix_textbox()
    beta_basic.add_output_folder_button()
    beta_basic.add_run_button("Run BETA Basic")
    beta_basic.add_reset_button()

    # Create BETA minus frame
    beta_minus = BetaFrame(notebook, type="minus", max_width=750)
    notebook.add(beta_minus, text="BETA Minus")

    beta_minus.add_description("Detect TF target genes based on regulatory potential score only by binding data.")
    beta_minus.add_cmd("BETA minus --pn 10000 -d 100000 -o ./")
    beta_minus.add_label("--------- REQUIRED PARAMETERS ---------", font=('Arial', 10, 'bold'), colspan=2)
    beta_minus.add_peaks_file_button()
    beta_minus.add_genome_dropdown()
    beta_minus.add_reference_file_button()
    beta_minus.add_label("--------- OPTIONAL PARAMETERS ---------", font=('Arial', 10, 'bold'), colspan=2)
    beta_minus.add_bl_checkbox()
    beta_minus.add_boundary_file_button()
    beta_minus.add_peak_number_textbox()
    beta_minus.add_distance_textbox()
    beta_minus.add_name_prefix_textbox()
    beta_minus.add_output_folder_button()
    beta_minus.add_run_button("Run BETA Minus")
    beta_minus.add_reset_button()

    beta_cite = BetaFrame(notebook, type="", max_width=750)
    notebook.add(beta_cite, text="Citation")
    beta_cite.add_label("BETA Paper:", font=('Arial', 12, "bold"), colspan=2, sticky='W')
    beta_cite.add_text("Wang, S., Sun, H., Ma, J., Zang, C., Wang, C., Wang, J., ... & Liu, X. S. (2013). Target analysis by integration of transcriptome and ChIP-seq data with BETA. Nature protocols, 8(12), 2502-2515.", font=('Arial', 12), width=80, height=2, colspan=2)
    beta_cite.add_label("BETA Documentation:", font=('Arial', 12, "bold"), colspan=2, sticky='W')
    beta_cite.add_text("http://cistrome.org/BETA/", font=('Arial', 12), colspan=2)
    beta_cite.add_label("GUI Contact:", font=('Arial', 12, "bold"), colspan=2, sticky='W')
    beta_cite.add_text("earezza@ohri.ca", font=('Arial', 12), colspan=2)
    beta_cite.add_text("https://github.com/earezza", font=('Arial', 12), colspan=2)

    # ===================================================================== #
    # Start the GUI event loop
    # ===================================================================== #
    root.mainloop()