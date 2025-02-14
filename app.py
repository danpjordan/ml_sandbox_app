import sys
import os
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QComboBox,
    QFileDialog,
    QLabel,
    QMessageBox,
    QCheckBox,
    QScrollArea,
    QLineEdit,
    QFormLayout,
    QSpinBox,
)

import pandas as pd
import dfhelper
import ml_source as ml

DEBUG_MODE = False

class MlProject(QWidget):
    def __init__(self):
        super().__init__()
        self.checkboxes = {}
        self.df = None
        self.selected_df_unmodifed = None
        self.selected_df = None
        self.targetVariable = None
        self.columns = None
        self.model_eval = None
        self.params = {
            'impute': True,
            'remove_invariants': True,
            'handle_outliers': True,
            'vif_threshold': 5,
            'encoding': 'onehot'
        }
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('ML Project')

        self.layout = QVBoxLayout()

        self.uploadButton = QPushButton('Upload CSV File', self)
        self.uploadButton.clicked.connect(self.uploadFile)
        self.layout.addWidget(self.uploadButton)

        self.fileNameLabel = QLabel('No file uploaded', self)
        self.layout.addWidget(self.fileNameLabel)

        self.selectColumnLabel = QLabel('Target Variable:', self)
        self.layout.addWidget(self.selectColumnLabel)

        self.selectColumnDropdown = QComboBox(self)
        self.selectColumnDropdown.currentIndexChanged.connect(self.updateCheckboxes)
        self.layout.addWidget(self.selectColumnDropdown)

        self.targetVariableStatus = QLabel('Status: ', self)
        self.layout.addWidget(self.targetVariableStatus)

        self.columnsLabel = QLabel('Select Features:', self)
        self.layout.addWidget(self.columnsLabel)

        self.scrollArea = QScrollArea(self)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaLayout = QVBoxLayout(self.scrollAreaWidgetContents)
        self.scrollArea.setMinimumHeight(200)
        self.layout.addWidget(self.scrollArea)

        self.selectAllButton = QPushButton('Select All', self)
        self.selectAllButton.clicked.connect(self.selectAllCheckboxes)
        self.layout.addWidget(self.selectAllButton)

        self.deselectAllButton = QPushButton('Deselect All', self)
        self.deselectAllButton.clicked.connect(self.deselectAllCheckboxes)
        self.layout.addWidget(self.deselectAllButton)

        # Add preprocessing parameters section
        self.paramsLabel = QLabel('Preprocessing Parameters:', self)
        self.layout.addWidget(self.paramsLabel)

        self.paramsLayout = QFormLayout()

        self.imputeCheckbox = QCheckBox('Impute Missing Values')
        self.imputeCheckbox.setChecked(self.params['impute'])
        self.imputeCheckbox.stateChanged.connect(self.updateParams)
        self.paramsLayout.addRow('Impute:', self.imputeCheckbox)

        self.removeInvariantsCheckbox = QCheckBox('Remove Invariant Features')
        self.removeInvariantsCheckbox.setChecked(self.params['remove_invariants'])
        self.removeInvariantsCheckbox.stateChanged.connect(self.updateParams)
        self.paramsLayout.addRow('Remove Invariants:', self.removeInvariantsCheckbox)

        self.handleOutliersCheckbox = QCheckBox('Handle Outliers')
        self.handleOutliersCheckbox.setChecked(self.params['handle_outliers'])
        self.handleOutliersCheckbox.stateChanged.connect(self.updateParams)
        self.paramsLayout.addRow('Handle Outliers:', self.handleOutliersCheckbox)

        self.vifThresholdSpinBox = QSpinBox()
        self.vifThresholdSpinBox.setValue(self.params['vif_threshold'])
        self.vifThresholdSpinBox.valueChanged.connect(self.updateParams)
        self.paramsLayout.addRow('VIF Threshold:', self.vifThresholdSpinBox)

        self.encodingComboBox = QComboBox()
        self.encodingComboBox.addItems(['onehot', 'label'])
        self.encodingComboBox.setCurrentText(self.params['encoding'])
        self.encodingComboBox.currentTextChanged.connect(self.updateParams)
        self.paramsLayout.addRow('Encoding:', self.encodingComboBox)

        self.layout.addLayout(self.paramsLayout)

        self.submitButton = QPushButton('Submit', self)
        self.submitButton.clicked.connect(self.submit)
        self.layout.addWidget(self.submitButton)

        self.setLayout(self.layout)
        self.setGeometry(300, 300, 400, 600)

    def uploadFile(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        fileName, _ = QFileDialog.getOpenFileName(self, "Open CSV File", "", "CSV Files (*.csv);;All Files (*)", options=options)
        if fileName:
            self.loadCSV(fileName)
            self.fileNameLabel.setText(f'Uploaded File: {os.path.basename(fileName)}')
         
    def loadCSV(self, fileName):
        self.df = pd.read_csv(fileName)
        self.header = self.df.columns.tolist()
        self.selectColumnDropdown.clear()
        self.selectColumnDropdown.addItems(self.header)
        self.loadCheckboxes()

    def loadCheckboxes(self):
        for i in reversed(range(self.scrollAreaLayout.count())):
            widget_to_remove = self.scrollAreaLayout.itemAt(i).widget()
            self.scrollAreaLayout.removeWidget(widget_to_remove)
            widget_to_remove.setParent(None)
        
        self.checkboxes = {}
        for column in self.header:
            checkbox = QCheckBox(column)
            checkbox.setChecked(True)
            self.checkboxes[column] = checkbox
            self.scrollAreaLayout.addWidget(checkbox)
        
        self.updateCheckboxes()

    def updateCheckboxes(self):
        self.target_variable = self.selectColumnDropdown.currentText()
        for column, checkbox in self.checkboxes.items():
            if column == self.target_variable:
                checkbox.setChecked(True)
                checkbox.setDisabled(True)
            else:
                checkbox.setDisabled(False)
        
        self.updateTargetVariableStatus()
        
    def updateTargetVariableStatus(self):
        try:
            data = self.df[self.target_variable].to_list()
            target_series = pd.Series(data)
            # Check if the target variable is discrete
            is_discrete = len(target_series.unique()) <= dfhelper.DISCRETE_THRESHOLD
            status = 'Discrete' if is_discrete else 'Continuous'
        except ValueError:
            # Handle case where target variable is not found in header
            status = 'Unknown'
        self.targetVariableStatus.setText(f'Status: {status}')
            
    def selectAllCheckboxes(self):
        for column, checkbox in self.checkboxes.items():
            if checkbox.isEnabled():
                checkbox.setChecked(True)

    def deselectAllCheckboxes(self):
        for column, checkbox in self.checkboxes.items():
            if checkbox.isEnabled():
                checkbox.setChecked(False)

    def perform_machine_learning(self):
        df, _ = ml.pre_process(df=self.selected_df_unmodifed, proj=self)
        support = ml.training_and_evaluation(df=df, proj=self)
        support['params'] = self.params
        self.model_eval = ml.ModelEvaluationApp(support)
        self.model_eval.show()

    def updateParams(self):
        self.params['impute'] = self.imputeCheckbox.isChecked()
        self.params['remove_invariants'] = self.removeInvariantsCheckbox.isChecked()
        self.params['handle_outliers'] = self.handleOutliersCheckbox.isChecked()
        self.params['vif_threshold'] = self.vifThresholdSpinBox.value()
        self.params['encoding'] = self.encodingComboBox.currentText()

    def submit(self):
        self.targetVariable = self.selectColumnDropdown.currentText()
        if not self.targetVariable:
            QMessageBox.warning(self, "No Selection", "Please select a special column from the dropdown list.")
            return

        selected_features = [col for col, checkbox in self.checkboxes.items() if checkbox.isChecked()]
        
        if self.targetVariable not in selected_features:
            selected_features.append(self.targetVariable)
        
        if DEBUG_MODE:
          for col in selected_features:
              if col != self.targetVariable:
                  print(col)
      
        if not self.df.empty:
            self.selected_df = self.df[selected_features].copy()
            
            for col in self.selected_df.columns:
              try:
                self.selected_df[col] = pd.to_numeric(self.selected_df[col])
              except ValueError:
                pass
            
            self.selected_df_unmodifed = self.selected_df.copy()
            
            self.columns = dfhelper.createColumnDict(self.selected_df)
            dfhelper.convertStringToInt(self.selected_df, self.columns)
            
            if DEBUG_MODE : dfhelper.printColumns(self.columns)

            # output the selected data as a csv
            self.selected_df.to_csv("output/out.csv", index=False)
            
            # output the unmodified selected data as a csv
            self.selected_df_unmodifed.to_csv("output/out_unmodifed.csv", index=False)
            
            # output the dictionaries as a txt
            dfhelper.outputDictionaries(self.columns)
            
            print("Dataframe created")
        else:
            print("No dataframe found")

        self.perform_machine_learning()
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MlProject()
    ex.show()
    sys.exit(app.exec_())
