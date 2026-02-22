# Complete Football Analytics

Welcome to the **Complete Football Analytics** repository! This project is a comprehensive resource for learning and applying data science and machine learning techniques specifically to football (soccer) data. It covers everything from Python basics to advanced web scraping, data visualization, and predictive modeling.

## 📂 Repository Structure

The repository is organized into progressive modules, taking you from a beginner level to building complex analytics projects.

### 📚 Modules

*   **Module 1: Python Fundamentals**
    *   Learn the core building blocks of Python programming.
    *   Covers: Syntax, Variables, Data Types, Control Flows (If/Else, Loops), Functions, and Error Handling.

*   **Module 3: Data Acquisition & Web Scraping**
    *   Master the art of gathering football data from various sources.
    *   **APIs & Libraries**: `Statsbombpy`, `Soccerdata`.
    *   **Scraping Targets**: FBRef, Sofascore, Understat, Fotmob, Whoscored.
    *   **Techniques**: Handling requests, parsing HTML with `BeautifulSoup`, and using browser automation tools like `Playwright` and `Undetected Chromedriver` etc.

*   **Module 4: Data Visualization**
    *   Create professional-grade football visualizations.
    *   **Libraries**: `Matplotlib`, `Seaborn`, and the specialized `mplsoccer` library.
    *   **Visualizations**:
        *   Scatter Plots, Heatmaps, and Radar Charts.
        *   "Pizza" Plots (Percentile Ranks).
        *   Pass Networks and Passmaps.
        *   Shotmaps and xG Flow Charts.
        *   Pitch plotting and grid layouts.

*   **Module 5: Data Analysis**
    *   Dive deep into data manipulation and statistical analysis.
    *   **Tools**: `Pandas` and `Numpy`.
    *   **Topics**: Data Cleaning, Basic Statistics, Correlation Analysis.

*   **Module 6: Machine Learning for Football**
    *   Apply ML algorithms to football data.
    *   **Concepts**: Supervised vs. Unsupervised Learning.
    *   **Applications**:
        *   **Classification**: Predicting categorical outcomes (e.g., match results).
        *   **Regression**: Predicting continuous values (e.g., player values, xG).
        *   **Clustering**: Grouping similar players or teams.
        *   Model Evaluation techniques.

### 🚀 Projects

Apply what you've learned in these comprehensive projects:

1.  **Project 1: Match Dashboards**: Build an interactive dashboard to analyze match performance.
2.  **Project 2: Match Prediction**: Develop a machine learning model to predict the outcome of football matches using historical data.

## 🛠️ Installation & Setup

To get started with this repository, you'll need Python installed. It is recommended to use a virtual environment.

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd BCNPROJECT-main
    ```

2.  **Install Dependencies**:
    The project relies on several powerful libraries. Install them using the provided `requirements.txt` file.
    ```bash
    pip install -r requirements.txt
    ```

    **Key Libraries Include:**
    *   `pandas`, `numpy`: Data manipulation.
    *   `matplotlib`, `seaborn`: General plotting.
    *   `mplsoccer`: Specialized football plotting.
    *   `soccerdata`, `statsbombpy`: Data access.
    *   `scikit-learn`: Machine learning.
    *   `playwright`: Browser automation (may require additional setup: `playwright install`).

## 📈 Usage

Most of the content is provided in **Jupyter Notebooks (`.ipynb`)**. To explore the modules:

1.  Launch Jupyter:
    ```bash
    jupyter notebook
    ```
2.  Navigate to the desired module directory.
3.  Open a notebook (e.g., `3.2 Statsbomb API.ipynb`) and run the cells.

## 🤝 Contributing

Feel free to fork this repository, submit Pull Requests, or open Issues if you find bugs or have suggestions for new analytics techniques!