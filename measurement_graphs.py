"""
measurement_graphs.py - Measurement history graphs using matplotlib
"""

import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd


class MeasurementGraphs:
    def __init__(self, parent_frame, csv_file="measurement_history.csv"):
        """
        Initialize measurement graphs
        
        Args:
            parent_frame: Tkinter frame to embed graphs
            csv_file: Path to measurement history CSV
        """
        self.parent = parent_frame
        self.csv_file = csv_file
        self.fig = None
        self.ax = None
        self.canvas = None
        
        # Check if pandas is available
        try:
            import pandas as pd
            self.pd = pd
            self.has_pandas = True
        except ImportError:
            self.has_pandas = False
            print("⚠️ pandas not installed. Graphs disabled.")
            print("   Install with: pip install pandas")
        
        self.setup_figure()
    
    def setup_figure(self):
        """Setup matplotlib figure with dark theme"""
        if not self.has_pandas:
            return
            
        plt.style.use('dark_background')
        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        self.fig.patch.set_facecolor('#1c2128')
        self.ax.set_facecolor('#0d1117')
        self.ax.tick_params(colors='white')
        
        # Style spines
        for spine in self.ax.spines.values():
            spine.set_color('white')
            spine.set_linewidth(0.5)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.parent)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
    
    def update_graph(self, measurement_type="both", units="cm"):
        """
        Update the graph with latest data
        
        Args:
            measurement_type: "width", "height", or "both"
            units: "cm" or "inches"
        """
        if not self.has_pandas:
            self._show_no_pandas_message()
            return
        
        if not os.path.exists(self.csv_file):
            self._show_no_data_message()
            return
        
        try:
            # Read CSV file
            df = self.pd.read_csv(self.csv_file)
            
            if len(df) == 0:
                self._show_no_data_message()
                return
            
            self.ax.clear()
            
            # Convert units if needed
            if units == "inches":
                widths = df['Width (cm)'] / 2.54
                heights = df['Height (cm)'] / 2.54
                y_label = f"Size (inches)"
            else:
                widths = df['Width (cm)']
                heights = df['Height (cm)']
                y_label = "Size (cm)"
            
            # Plot based on type
            if measurement_type == "width":
                self.ax.plot(widths.values, 'o-', label='Width', 
                            linewidth=2, markersize=6, color='#22c55e')
            elif measurement_type == "height":
                self.ax.plot(heights.values, 'o-', label='Height',
                            linewidth=2, markersize=6, color='#3b82f6')
            else:
                self.ax.plot(widths.values, 'o-', label='Width',
                            linewidth=2, markersize=6, color='#22c55e')
                self.ax.plot(heights.values, 'o-', label='Height',
                            linewidth=2, markersize=6, color='#3b82f6')
            
            # Labels and title
            self.ax.set_xlabel("Measurement Number", color='white', fontsize=10)
            self.ax.set_ylabel(y_label, color='white', fontsize=10)
            self.ax.set_title("Measurement History", color='#00e5ff', fontsize=12, fontweight='bold')
            self.ax.legend(loc='upper right', facecolor='#1c2128', edgecolor='white')
            self.ax.grid(True, alpha=0.3, linestyle='--')
            
            # Set y-axis limit with margin
            if measurement_type == "width":
                max_val = widths.max() if len(widths) > 0 else 10
                self.ax.set_ylim(0, max_val * 1.2)
            elif measurement_type == "height":
                max_val = heights.max() if len(heights) > 0 else 20
                self.ax.set_ylim(0, max_val * 1.2)
            
            self.canvas.draw()
            
        except Exception as e:
            print(f"Graph update error: {e}")
            self._show_error_message(str(e))
    
    def plot_object_trends(self, object_name=None):
        """
        Plot trends for specific object type
        
        Args:
            object_name: Name of object to filter (None for all)
        """
        if not self.has_pandas:
            self._show_no_pandas_message()
            return
        
        if not os.path.exists(self.csv_file):
            self._show_no_data_message()
            return
        
        try:
            df = self.pd.read_csv(self.csv_file)
            
            if len(df) == 0:
                self._show_no_data_message()
                return
            
            # Filter by object name if specified
            if object_name:
                df = df[df['Object Name'] == object_name]
            
            if len(df) == 0:
                self.ax.clear()
                self.ax.text(0.5, 0.5, f"No data for '{object_name}'", 
                           ha='center', va='center', color='white', fontsize=12)
                self.canvas.draw()
                return
            
            # Convert Date column to datetime
            df['Date'] = self.pd.to_datetime(df['Date'])
            
            # Group by date and calculate averages
            daily_avg = df.groupby(df['Date'].dt.date).agg({
                'Width (cm)': 'mean',
                'Height (cm)': 'mean'
            }).reset_index()
            
            self.ax.clear()
            
            # Plot trends
            self.ax.plot(daily_avg['Date'], daily_avg['Width (cm)'], 
                        'o-', label='Avg Width', color='#22c55e', linewidth=2, markersize=6)
            self.ax.plot(daily_avg['Date'], daily_avg['Height (cm)'], 
                        'o-', label='Avg Height', color='#3b82f6', linewidth=2, markersize=6)
            
            # Formatting
            self.ax.set_xlabel("Date", color='white', fontsize=10)
            self.ax.set_ylabel("Size (cm)", color='white', fontsize=10)
            self.ax.set_title(f"Object Trends - {object_name if object_name else 'All Objects'}", 
                            color='#00e5ff', fontsize=12, fontweight='bold')
            self.ax.legend(loc='upper right', facecolor='#1c2128', edgecolor='white')
            self.ax.grid(True, alpha=0.3, linestyle='--')
            
            # Rotate date labels for better readability
            plt.setp(self.ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            self.canvas.draw()
            
        except Exception as e:
            print(f"Object trends error: {e}")
            self._show_error_message(str(e))
    
    def plot_object_comparison(self):
        """Plot comparison of different object types"""
        if not self.has_pandas:
            self._show_no_pandas_message()
            return
        
        if not os.path.exists(self.csv_file):
            self._show_no_data_message()
            return
        
        try:
            df = self.pd.read_csv(self.csv_file)
            
            if len(df) == 0:
                self._show_no_data_message()
                return
            
            # Get average measurements by object type
            object_stats = df.groupby('Object Name').agg({
                'Width (cm)': 'mean',
                'Height (cm)': 'mean',
                'Confidence': 'mean'
            }).reset_index()
            
            if len(object_stats) == 0:
                return
            
            self.ax.clear()
            
            # Create bar chart
            x = range(len(object_stats))
            width = 0.35
            
            bars1 = self.ax.bar([i - width/2 for i in x], object_stats['Width (cm)'], 
                               width, label='Width', color='#22c55e')
            bars2 = self.ax.bar([i + width/2 for i in x], object_stats['Height (cm)'], 
                               width, label='Height', color='#3b82f6')
            
            # Add value labels on bars
            for bar in bars1:
                height = bar.get_height()
                self.ax.annotate(f'{height:.1f}',
                               xy=(bar.get_x() + bar.get_width() / 2, height),
                               xytext=(0, 3), textcoords="offset points",
                               ha='center', va='bottom', color='white', fontsize=8)
            
            for bar in bars2:
                height = bar.get_height()
                self.ax.annotate(f'{height:.1f}',
                               xy=(bar.get_x() + bar.get_width() / 2, height),
                               xytext=(0, 3), textcoords="offset points",
                               ha='center', va='bottom', color='white', fontsize=8)
            
            self.ax.set_xlabel("Object Type", color='white', fontsize=10)
            self.ax.set_ylabel("Size (cm)", color='white', fontsize=10)
            self.ax.set_title("Object Size Comparison", color='#00e5ff', fontsize=12, fontweight='bold')
            self.ax.set_xticks(x)
            self.ax.set_xticklabels(object_stats['Object Name'], rotation=45, ha='right', color='white')
            self.ax.legend(loc='upper right', facecolor='#1c2128', edgecolor='white')
            self.ax.grid(True, alpha=0.3, axis='y', linestyle='--')
            
            self.canvas.draw()
            
        except Exception as e:
            print(f"Object comparison error: {e}")
            self._show_error_message(str(e))
    
    def plot_accuracy_distribution(self):
        """Plot accuracy distribution of measurements"""
        if not self.has_pandas:
            self._show_no_pandas_message()
            return
        
        if not os.path.exists(self.csv_file):
            self._show_no_data_message()
            return
        
        try:
            df = self.pd.read_csv(self.csv_file)
            
            if len(df) == 0:
                return
            
            # Get accuracy distribution
            accuracy_counts = df['Accuracy'].value_counts()
            
            self.ax.clear()
            
            # Colors for different accuracy levels
            colors = {
                'High': '#22c55e',
                'Medium': '#f59e0b', 
                'Low': '#ef4444',
                'Estimated': '#8b949e'
            }
            
            bar_colors = [colors.get(acc, '#8b949e') for acc in accuracy_counts.index]
            
            bars = self.ax.bar(accuracy_counts.index, accuracy_counts.values, color=bar_colors, edgecolor='white', linewidth=1)
            
            # Add count labels
            for bar in bars:
                height = bar.get_height()
                self.ax.annotate(f'{int(height)}',
                               xy=(bar.get_x() + bar.get_width() / 2, height),
                               xytext=(0, 3), textcoords="offset points",
                               ha='center', va='bottom', color='white', fontsize=10, fontweight='bold')
            
            self.ax.set_xlabel("Accuracy Level", color='white', fontsize=10)
            self.ax.set_ylabel("Number of Measurements", color='white', fontsize=10)
            self.ax.set_title("Measurement Accuracy Distribution", color='#00e5ff', fontsize=12, fontweight='bold')
            self.ax.grid(True, alpha=0.3, axis='y', linestyle='--')
            
            self.canvas.draw()
            
        except Exception as e:
            print(f"Accuracy distribution error: {e}")
    
    def refresh(self):
        """Refresh the current graph"""
        self.update_graph()
    
    def _show_no_data_message(self):
        """Show message when no data available"""
        self.ax.clear()
        self.ax.text(0.5, 0.5, "No measurement data available\n\nMake some measurements first!", 
                   ha='center', va='center', color='white', fontsize=12,
                   transform=self.ax.transAxes)
        self.ax.set_facecolor('#0d1117')
        self.canvas.draw()
    
    def _show_error_message(self, error_msg):
        """Show error message in graph"""
        self.ax.clear()
        self.ax.text(0.5, 0.5, f"Error loading data:\n{error_msg}", 
                   ha='center', va='center', color='red', fontsize=10,
                   transform=self.ax.transAxes)
        self.canvas.draw()
    
    def _show_no_pandas_message(self):
        """Show message when pandas is not installed"""
        self.ax.clear()
        self.ax.text(0.5, 0.5, "pandas not installed\n\nInstall with: pip install pandas", 
                   ha='center', va='center', color='yellow', fontsize=10,
                   transform=self.ax.transAxes)
        self.canvas.draw()