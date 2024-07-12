import sys
import stomp
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, \
    QTreeWidget, QTreeWidgetItem, QHBoxLayout, QMenuBar, QAction, QSplitter, QTextEdit, QLabel, QScrollArea, \
    QPushButton, QInputDialog, QMessageBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal


class ActiveMQListener(stomp.ConnectionListener):
    def __init__(self, client):
        self.client = client

    def on_error(self, frame):
        print('received an error:', frame.body)

    def on_message(self, frame):
        self.client.process_message(frame.body)


class ActiveMQClient(QThread):
    message_received = pyqtSignal(str)

    def __init__(self, host, port, topic):
        super().__init__()
        self.host = host
        self.port = port
        self.topic = topic
        self.conn = None

    def run(self):
        self.conn = stomp.Connection([(self.host, self.port)])
        self.conn.set_listener('', ActiveMQListener(self))
        self.conn.start()
        self.conn.connect('admin', 'admin', wait=True)
        self.conn.subscribe(destination=self.topic, id=1, ack='auto')

        while True:
            time.sleep(1)

    def process_message(self, message):
        self.message_received.emit(message)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ActiveMQ 客户端")
        self.setGeometry(100, 100, 1200, 800)

        self.active_mq_clients = {}  # 存储所有的ActiveMQ客户端

        # 创建菜单栏
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('文件')
        tools_menu = menu_bar.addMenu('功能诊断')
        log_menu = menu_bar.addMenu('日志分析')
        help_menu = menu_bar.addMenu('帮助')

        # 创建主布局
        main_layout = QVBoxLayout()

        # 创建上方布局
        upper_layout = QHBoxLayout()

        # 创建左侧树形视图
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.populate_tree()

        # 创建按钮布局
        button_layout = QVBoxLayout()
        self.create_connection_button = QPushButton("创建MQ连接")
        self.create_connection_button.clicked.connect(self.create_mq_connection)
        self.delete_connection_button = QPushButton("删除MQ连接")
        self.delete_connection_button.clicked.connect(self.delete_mq_connection)

        button_layout.addWidget(self.create_connection_button)
        button_layout.addWidget(self.delete_connection_button)

        # 添加按钮和树形视图到左侧布局
        left_layout = QVBoxLayout()
        left_layout.addLayout(button_layout)
        left_layout.addWidget(self.tree_widget)

        # 创建表格视图
        self.table_widget = QTableWidget()
        self.table_widget.setRowCount(0)  # 初始化为空表格
        self.table_widget.setColumnCount(6)
        self.table_widget.setHorizontalHeaderLabels(["接收时间", "ID", "类型", "通知源", "IP", "消息索引"])
        self.table_widget.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_widget.setSelectionMode(QTableWidget.SingleSelection)
        self.table_widget.clicked.connect(self.on_table_item_click)

        # 使用分割器布局
        left_container = QWidget()
        left_container.setLayout(left_layout)
        right_container = QWidget()
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.table_widget)
        right_container.setLayout(right_layout)

        top_splitter = QSplitter(Qt.Horizontal)
        top_splitter.addWidget(left_container)
        top_splitter.addWidget(right_container)
        top_splitter.setSizes([300, 900])  # 左侧1/4，右侧3/4

        # 创建下方的详细信息展示区域
        self.detail_label = QLabel("详细信息:")
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)

        # 将详细信息界面放入一个滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        detail_container = QWidget()
        detail_layout = QVBoxLayout(detail_container)
        detail_layout.addWidget(self.detail_label)
        detail_layout.addWidget(self.detail_text)
        scroll_area.setWidget(detail_container)

        # 使用垂直分割器布局
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(scroll_area)
        main_splitter.setSizes([600, 200])  # 上面3/4，下面1/4

        main_layout.addWidget(main_splitter)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def populate_tree(self):
        root = QTreeWidgetItem(self.tree_widget, ["MQ Connections"])
        self.tree_widget.expandAll()

    def create_mq_connection(self):
        host, ok = QInputDialog.getText(self, 'MQ连接', '请输入MQ服务器地址（例如：10.0.0.100）:')
        if not ok:
            return
        port, ok = QInputDialog.getInt(self, 'MQ连接', '请输入MQ服务器端口（例如：61616）:')
        if not ok:
            return

        connection_url = f"tcp://{host}:{port}"
        root = self.tree_widget.topLevelItem(0)
        connection_item = QTreeWidgetItem(root, [connection_url])

        # 这里模拟一些可订阅的topic
        topics = ["/topic/test1", "/topic/test2", "/topic/test3"]
        for topic in topics:
            topic_item = QTreeWidgetItem(connection_item, [topic])
            topic_item.setData(0, Qt.UserRole, (host, port, topic))

        self.tree_widget.expandAll()

    def delete_mq_connection(self):
        selected_item = self.tree_widget.currentItem()
        if selected_item and selected_item.parent():
            parent = selected_item.parent()
            if parent.text(0).startswith("tcp://"):
                index = parent.indexOfChild(selected_item)
                parent.takeChild(index)

                # 停止并删除对应的ActiveMQ客户端
                if (host, port, topic) in self.active_mq_clients:
                    self.active_mq_clients[(host, port, topic)].terminate()
                    del self.active_mq_clients[(host, port, topic)]

    def on_tree_item_click(self, item, column):
        data = item.data(0, Qt.UserRole)
        if data:
            host, port, topic = data
            if (host, port, topic) not in self.active_mq_clients:
                self.active_mq_clients[(host, port, topic)] = ActiveMQClient(host, port, topic)
                self.active_mq_clients[(host, port, topic)].message_received.connect(self.add_message_to_table)
                self.active_mq_clients[(host, port, topic)].start()

            # 清空表格
            self.table_widget.setRowCount(0)

    def add_message_to_table(self, message):
        new_row_idx = self.table_widget.rowCount()
        self.table_widget.insertRow(new_row_idx)
        columns = message.split(',')
        for col_idx, col_data in enumerate(columns):
            self.table_widget.setItem(new_row_idx, col_idx, QTableWidgetItem(col_data))

    def on_table_item_click(self, index):
        row = index.row()
        detail = ""
        for col in range(self.table_widget.columnCount()):
            detail += f"{self.table_widget.horizontalHeaderItem(col).text()}: {self.table_widget.item(row, col).text()}\n"
        self.detail_text.setText(detail)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
