from datetime import datetime
from typing import Optional, List
import pandas as pd
import asyncio
import time
import os


class MedicalDevice:
    """Класс для хранения данных об одном медицинском устройстве."""

    def __init__(
            self,
            device_id: str,
            clinic_id: str,
            clinic_name: str,
            city: str,
            department: str,
            model: str,
            serial_number: str,
            install_date: datetime,
            status: str = 'unknown',
            warranty_until: Optional[datetime] = None,
            last_calibration_date: Optional[datetime] = None,
            last_service_date: Optional[datetime] = None,
            issues_reported_12mo: int = 0,
            failure_count_12mo: int = 0,
            uptime_pct: float = 100.0,
            issues_text: Optional[str] = None,
            status_normalized: str = 'unknown',
            warranty_expired: bool = False,
            next_calibration: Optional[datetime] = None,
            calibration_status: str = 'unknown',
            calibration_error: bool = False
    ):
        """Инициализация объекта медицинского устройства.

        Args:
            device_id: Уникальный идентификатор устройства.
            clinic_id: Уникальный идентификатор клиники.
            clinic_name: Название клиники.
            city: Город расположения клиники.
            department: Медицинское отделение клиники.
            model: Модель устройства.
            serial_number: Серийный номер устройства.
            install_date: Дата установки оборудования в клинике.
            status: Текущий статус устройства (по умолчанию 'unknown').
            warranty_until: Дата окончания гарантии производителя (по умолчанию None).
            last_calibration_date: Дата последней калибровки оборудования (по умолчанию None).
            last_service_date: Дата последнего технического обслуживания (по умолчанию None).
            issues_reported_12mo: Количество проблем за последние 12 месяцев (по умолчанию 0).
            failure_count_12mo: Количество отказов за последние 12 месяцев (по умолчанию 0).
            uptime_pct: Процент работоспособности устройства (по умолчанию 100.0).
            issues_text: Текстовое описание проблем (по умолчанию None).
            status_normalized: Нормализованный статус устройства (по умолчанию 'unknown').
            warranty_expired: Флаг истёкшей гарантии (по умолчанию False).
            next_calibration: Дата следующей плановой калибровки (по умолчанию None).
            calibration_status: Статус калибровки устройства (по умолчанию 'unknown').
            calibration_error: Флаг ошибки калибровки (по умолчанию False).
        ."""
        self.device_id = device_id
        self.clinic_id = clinic_id
        self.clinic_name = clinic_name
        self.city = city
        self.department = department
        self.model = model
        self.serial_number = serial_number
        self.install_date = install_date
        self.warranty_until = warranty_until
        self.last_calibration_date = last_calibration_date
        self.last_service_date = last_service_date
        self.status = status
        self.status_normalized = status_normalized
        self.issues_reported_12mo = issues_reported_12mo
        self.failure_count_12mo = failure_count_12mo
        self.uptime_pct = uptime_pct
        self.issues_text = issues_text
        self.warranty_expired = warranty_expired
        self.calibration_error = calibration_error
        self.next_calibration = next_calibration
        self.calibration_status = calibration_status

    def is_operational(self) -> bool:
        """Проверка: устройство работает.

        Returns:
            True или False.
        """

        return self.status_normalized in ['operational', 'maintenance_scheduled']

    def is_faulty(self) -> bool:
        """Проверка: устройство неисправно.

        Returns:
            True или False.
        """

        return self.status_normalized == 'faulty'

    def is_warranty_valid(self) -> bool:
        """Проверка: гарантия действительна.

        Returns:
            True или False.
        """
        if self.warranty_until is None:

            return True

        return not self.warranty_expired

    def needs_calibration(self) -> bool:
        """Проверка: требуется калибровка.

        Returns:
            True или False.
        """

        return self.calibration_status in ['overdue', 'due_soon', 'no_record']

    def get_problem_score(self) -> float:
        """Расчёт индекса проблемности устройства.

        Returns:
            Индекс проблемности устройства.
        """
        score = 0
        score += self.issues_reported_12mo
        score += self.failure_count_12mo * 2
        if self.is_faulty():
            score += 3
        score += (100 - self.uptime_pct) * 0.5

        return score


def load_data_sync(filepath: str) -> pd.DataFrame:
    """Загрузка и первичная обработка данных из Excel.

    Args:
        filepath: Путь к файлу Excel.

    Returns:
        DataFrame.
    """
    df = pd.read_excel(filepath)
    df.columns = df.columns.str.lower()
    df.columns = df.columns.str.strip()
    df = df.drop_duplicates(subset=['device_id'], keep='first')
    print(f"Загружено записей: {len(df)} из {filepath.split('/')[-1]}")

    return df


def load_all_files_sync(folder_path: str) -> pd.DataFrame:
    """Загрузка всех Excel файлов из папки последовательно.

    Args:
        folder_path: Путь к папке с Excel файлами.

    Returns:
        DataFrame со всеми данными из всех файлов.
    """
    files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.xlsx')]

    if not files:
        raise ValueError(f"Файлы .xlsx не найдены в папке {folder_path}")

    print(f"Найдено файлов: {len(files)}")
    print("Последовательная загрузка...")

    dfs = []
    for file in files:
        df = load_data_sync(file)
        dfs.append(df)

    combined_df = pd.concat(dfs, ignore_index=True)
    combined_df = combined_df.drop_duplicates(subset=['device_id'], keep='first')

    print(f"Всего уникальных устройств: {len(combined_df)}")

    return combined_df


def normalize_status_sync(df: pd.DataFrame) -> pd.DataFrame:
    """Нормализация статусов устройств."""
    status_map = {
        'operational': 'operational', 'ok': 'operational', 'op': 'operational',
        'working': 'operational', 'planned_installation': 'planned_installation',
        'planned': 'planned_installation', 'maintenance_scheduled': 'maintenance_scheduled',
        'maintenance': 'maintenance_scheduled', 'maint_sched': 'maintenance_scheduled',
        'service_scheduled': 'maintenance_scheduled', 'faulty': 'faulty',
        'broken': 'faulty', 'needs_repair': 'faulty', 'fault': 'faulty',
    }

    df['status_normalized'] = (
        df['status'].astype(str).str.lower().str.strip()
        .map(lambda x: status_map.get(x, 'unknown'))
    )

    status_counts = df['status_normalized'].value_counts()
    print("\nРаспределение статусов после нормализации:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")

    return df


def process_data_sync(df: pd.DataFrame) -> pd.DataFrame:
    """Обрабатывает данные DataFrame: парсит даты и добавляет флаги ошибок.

    Args:
        df: DataFrame.

    Returns:
        Тот же DataFrame с добавленными колонками.
    """
    date_cols = ['install_date', 'warranty_until', 'last_calibration_date', 'last_service_date']
    for col in date_cols:
        df[f'{col}_parsed'] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)

    df['calibration_error'] = (
            df['last_calibration_date_parsed'].notna()
            & df['install_date_parsed'].notna()
            & (df['last_calibration_date_parsed'] < df['install_date_parsed'])
    )

    df['warranty_expired'] = (
            df['warranty_until_parsed'].notna()
            & (df['warranty_until_parsed'] < datetime.now())
    )

    return df


def filter_by_warranty_sync(df: pd.DataFrame) -> pd.DataFrame:
    """Фильтрация устройств по гарантии.

    Args:
        df: DataFrame.

    Returns:
        DataFrame с отфильтрованными устройствами.
    """
    df_warranty = df[
        (df['warranty_expired'] == False) | (df['warranty_until_parsed'].isna())
        ].copy()

    return df_warranty


def analyze_clinics_sync(df: pd.DataFrame) -> pd.DataFrame:
    """Анализ проблем по клиникам.

    Args:
        df: DataFrame.

    Returns:
        DataFrame с топ-10 клиник, отсортированных по индексу проблемности.
    """
    clinic_problems = df.groupby(['clinic_id', 'clinic_name', 'city']).agg({
        'device_id': 'count',
        'issues_reported_12mo': 'sum',
        'failure_count_12mo': 'sum',
        'uptime_pct': 'mean',
        'status_normalized': lambda x: (x == 'faulty').sum()
    }).rename(columns={
        'device_id': 'total_device',
        'issues_reported_12mo': 'total_issues',
        'failure_count_12mo': 'total_failures',
        'uptime_pct': 'avg_uptime_pct',
        'status_normalized': 'faulty_count',
    }).reset_index()

    clinic_problems['problem_score'] = (
            clinic_problems['total_issues'] * 1 +
            clinic_problems['total_failures'] * 2 +
            clinic_problems['faulty_count'] * 3 +
            (100 - clinic_problems['avg_uptime_pct']) * 0.5
    )
    clinic_problems = clinic_problems.sort_values('problem_score', ascending=False)

    return clinic_problems.head(10)


def generate_calibration_report_sync(df: pd.DataFrame) -> tuple:
    """Генерация отчёта по калибровке.

    Args:
        df: DataFrame.

    Returns:
        Кортеж из двух DataFrame:
        - calibration_report;
        - overdue_devices.
    """
    df = df.copy()
    df['next_calibration'] = df['last_calibration_date_parsed'] + pd.DateOffset(months=12)
    today = pd.Timestamp(datetime.now().date())

    def calib_status(row):
        if pd.isna(row['last_calibration_date_parsed']):

            return 'no_record'

        elif pd.isna(row['next_calibration']):

            return 'unknown'

        elif row['next_calibration'] < today:

            return 'overdue'

        elif row['next_calibration'] < today + pd.Timedelta(days=30):

            return 'due_soon'

        return 'ok'

    df['calibration_status'] = df.apply(calib_status, axis=1)
    calibration_report = df[
        df['status_normalized'].isin(['operational', 'maintenance_scheduled'])
    ][['device_id', 'clinic_name', 'model', 'last_calibration_date_parsed',
       'next_calibration', 'calibration_status']]
    overdue_devices = calibration_report[calibration_report['calibration_status'] == 'overdue']

    return calibration_report, overdue_devices


def create_pivot_table_sync(df: pd.DataFrame) -> tuple:
    """Создание сводных таблиц.

    Args:
        df: DataFrame.

    Returns:
        Кортеж из четырёх DataFrame:
        - pivot_clinic;
        - pivot_model;
        - device_table;
        - pivot_matrix.
    """
    pivot_clinic = df.groupby(['clinic_id', 'clinic_name', 'city']).agg({
        'device_id': 'count', 'issues_reported_12mo': 'sum',
        'failure_count_12mo': 'sum', 'uptime_pct': 'mean', 'model': 'nunique'
    }).reset_index()

    pivot_model = df.groupby(['model']).agg({
        'device_id': 'count', 'clinic_id': 'nunique',
        'issues_reported_12mo': 'sum', 'failure_count_12mo': 'sum',
        'uptime_pct': 'mean', 'warranty_expired': 'sum'
    }).reset_index()

    device_table = df[['device_id', 'clinic_id', 'clinic_name', 'city', 'department',
                       'model', 'serial_number', 'install_date_parsed', 'status_normalized',
                       'warranty_until_parsed', 'last_calibration_date_parsed',
                       'last_service_date_parsed', 'issues_reported_12mo',
                       'failure_count_12mo', 'uptime_pct', 'issues_text']]

    pivot_matrix = pd.pivot_table(
        df, values='device_id', index=['clinic_name', 'city'],
        columns=['model'], aggfunc='count', fill_value=0, margins=True
    )

    return pivot_clinic, pivot_model, device_table, pivot_matrix


def df_to_devices_sync(df: pd.DataFrame) -> List[MedicalDevice]:
    """Преобразование DataFrame в список объектов MedicalDevice.

    Args:
        df: DataFrame.

    Returns:
        Список объектов MedicalDevice.
    """
    devices = []

    for idx, row in df.iterrows():
        device = MedicalDevice(
            device_id=str(row.get('device_id', '')),
            clinic_id=str(row.get('clinic_id', '')),
            clinic_name=str(row.get('clinic_name', '')),
            city=str(row.get('city', '')),
            department=str(row.get('department', '')),
            model=str(row.get('model', '')),
            serial_number=str(row.get('serial_number', '')),
            install_date=pd.to_datetime(row.get('install_date'), errors='coerce'),
            warranty_until=pd.to_datetime(row.get('warranty_until'), errors='coerce'),
            last_calibration_date=pd.to_datetime(row.get('last_calibration_date'), errors='coerce'),
            last_service_date=pd.to_datetime(row.get('last_service_date'), errors='coerce'),
            status=str(row.get('status', 'unknown')),
            status_normalized=str(row.get('status_normalized', 'unknown')),
            issues_reported_12mo=int(row.get('issues_reported_12mo', 0) or 0),
            failure_count_12mo=int(row.get('failure_count_12mo', 0) or 0),
            uptime_pct=float(row.get('uptime_pct', 100.0) or 100.0),
            issues_text=str(row.get('issues_text', '')) if pd.notna(row.get('issues_text')) else None
        )
        devices.append(device)

    print(f"Создано объектов MedicalDevice: {len(devices)}")

    return devices


def export_to_excel_sync(data_dict: dict, filepath: str):
    """Экспорт всех результатов в Excel

     Args:
        data_dict;
        filepath.
    """
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        for sheet_name, df in data_dict.items():
            if isinstance(df, pd.DataFrame):
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                df.to_excel(writer, sheet_name=sheet_name)
    print(f"Сохранено в {filepath}")


def run_analysis_sync(folder_path: str) -> dict:
    """Главная функция анализа (синхронная).

    Args:
        folder_path: Путь к папке с Excel файлами.

    Returns:
        Словарь с результатами анализа, содержащий:
            - processed_df: Обработанный DataFrame с данными
            - warranty_df: DataFrame с устройствами на гарантии
            - top_clinics: DataFrame с топ-10 проблемных клиник
            - calibration_report: DataFrame с отчётом по калибровке
            - overdue_devices: DataFrame с просроченной калибровкой
            - devices: Список объектов MedicalDevice
    """
    df = load_all_files_sync(folder_path)


    df = normalize_status_sync(df)
    df = process_data_sync(df)


    top_clinics = analyze_clinics_sync(df)
    calibration_report, overdue_devices = generate_calibration_report_sync(df)
    pivot_clinic, pivot_model, device_table, pivot_matrix = create_pivot_table_sync(df)


    df_warranty = filter_by_warranty_sync(df)
    devices = df_to_devices_sync(df)


    export_to_excel_sync({
        'raw_data': df,
        'top_clinics': top_clinics,
        'calibration_report': calibration_report,
        'overdue_devices': overdue_devices,
        'by_clinic': pivot_clinic,
        'by_model': pivot_model,
        'device_details': device_table,
        'clinic_model_matrix': pivot_matrix
    }, 'medical_devices_report_sync.xlsx')

    print(f"\nВсего устройств: {len(df)}")
    print(f"Клиник: {df['clinic_id'].nunique()}")
    print(f"Устройств на гарантии: {len(df_warranty)}")
    print(f"Просроченная калибровка: {len(overdue_devices)}")
    print("Топ-5 проблемных клиник:")
    print(top_clinics[['clinic_name', 'city', 'problem_score']].head())

    return {
        'processed_df': df,
        'warranty_df': df_warranty,
        'top_clinics': top_clinics,
        'calibration_report': calibration_report,
        'overdue_devices': overdue_devices,
        'devices': devices
    }

async def load_data_async(filepath: str) -> pd.DataFrame:
    """Загрузка и первичная обработка данных из Excel.

    Args:
        filepath: Путь к файлу Excel.

    Returns:
        DataFrame.
    """
    df = pd.read_excel(filepath)
    df.columns = df.columns.str.lower()
    df.columns = df.columns.str.strip()
    df = df.drop_duplicates(subset=['device_id'], keep='first')
    print(f"Загружено записей: {len(df)} из {filepath.split('/')[-1]}")

    return df


async def load_all_files_async(folder_path: str) -> pd.DataFrame:
    """Загрузка всех Excel файлов из папки параллельно.

    Args:
        folder_path: Путь к папке с Excel файлами.

    Returns:
        DataFrame.
    """
    files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.xlsx')]

    if not files:
        raise ValueError(f"Файлы .xlsx не найдены в папке {folder_path}")

    print(f"Найдено файлов: {len(files)}")

    tasks = [load_data_async(file) for file in files]
    results = await asyncio.gather(*tasks)

    combined_df = pd.concat(results, ignore_index=True)
    combined_df = combined_df.drop_duplicates(subset=['device_id'], keep='first')

    print(f"Всего уникальных устройств: {len(combined_df)}")
    return combined_df


async def normalize_status_async(df: pd.DataFrame) -> pd.DataFrame:
    """Нормализация статусов устройств."""
    await asyncio.sleep(0)
    status_map = {
        'operational': 'operational', 'ok': 'operational', 'op': 'operational',
        'working': 'operational', 'planned_installation': 'planned_installation',
        'planned': 'planned_installation', 'maintenance_scheduled': 'maintenance_scheduled',
        'maintenance': 'maintenance_scheduled', 'maint_sched': 'maintenance_scheduled',
        'service_scheduled': 'maintenance_scheduled', 'faulty': 'faulty',
        'broken': 'faulty', 'needs_repair': 'faulty', 'fault': 'faulty',
    }

    df['status_normalized'] = (
        df['status'].astype(str).str.lower().str.strip()
        .map(lambda x: status_map.get(x, 'unknown'))
    )

    status_counts = df['status_normalized'].value_counts()
    print("Распределение статусов после нормализации:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")

    return df


async def process_data_async(df: pd.DataFrame) -> pd.DataFrame:
    """Обрабатывает данные: парсит даты и добавляет флаги ошибок."""
    await asyncio.sleep(0)
    date_cols = ['install_date', 'warranty_until', 'last_calibration_date', 'last_service_date']
    for col in date_cols:
        df[f'{col}_parsed'] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)

    df['calibration_error'] = (
            df['last_calibration_date_parsed'].notna()
            & df['install_date_parsed'].notna()
            & (df['last_calibration_date_parsed'] < df['install_date_parsed'])
    )

    df['warranty_expired'] = (
            df['warranty_until_parsed'].notna()
            & (df['warranty_until_parsed'] < datetime.now())
    )

    return df


async def filter_by_warranty_async(df: pd.DataFrame) -> pd.DataFrame:
    """Фильтрация устройств по гарантии."""
    await asyncio.sleep(0)
    df_warranty = df[
        (df['warranty_expired'] == False) | (df['warranty_until_parsed'].isna())

        ].copy()

    return df_warranty


async def analyze_clinics_async(df: pd.DataFrame) -> pd.DataFrame:
    """Анализ проблем по клиникам.

    Args:
        df: DataFrame.

    Returns:
        DataFrame с топ-5 клиник, отсортированных по индексу проблемности.
    """
    await asyncio.sleep(0)
    clinic_problems = df.groupby(['clinic_id', 'clinic_name', 'city']).agg({
        'device_id': 'count',
        'issues_reported_12mo': 'sum',
        'failure_count_12mo': 'sum',
        'uptime_pct': 'mean',
        'status_normalized': lambda x: (x == 'faulty').sum()
    }).rename(columns={
        'device_id': 'total_device',
        'issues_reported_12mo': 'total_issues',
        'failure_count_12mo': 'total_failures',
        'uptime_pct': 'avg_uptime_pct',
        'status_normalized': 'faulty_count',
    }).reset_index()

    clinic_problems['problem_score'] = (
            clinic_problems['total_issues'] * 1 +
            clinic_problems['total_failures'] * 2 +
            clinic_problems['faulty_count'] * 3 +
            (100 - clinic_problems['avg_uptime_pct']) * 0.5
    )
    clinic_problems = clinic_problems.sort_values('problem_score', ascending=False)

    return clinic_problems.head(10)


async def generate_calibration_report_async(df: pd.DataFrame) -> tuple:
    """Генерация отчёта по калибровке.

    Args:
        df: DataFrame.

    Returns:
        Кортеж из двух DataFrame:
        - calibration_report;
        - overdue_devices.
    """
    await asyncio.sleep(0)
    df = df.copy()
    df['next_calibration'] = df['last_calibration_date_parsed'] + pd.DateOffset(months=12)
    today = pd.Timestamp(datetime.now().date())

    def calib_status(row):
        if pd.isna(row['last_calibration_date_parsed']):

            return 'no_record'

        elif pd.isna(row['next_calibration']):

            return 'unknown'

        elif row['next_calibration'] < today:

            return 'overdue'

        elif row['next_calibration'] < today + pd.Timedelta(days=30):

            return 'due_soon'

        return 'ok'

    df['calibration_status'] = df.apply(calib_status, axis=1)
    calibration_report = df[
        df['status_normalized'].isin(['operational', 'maintenance_scheduled'])
    ][['device_id', 'clinic_name', 'model', 'last_calibration_date_parsed',
       'next_calibration', 'calibration_status']]
    overdue_devices = calibration_report[calibration_report['calibration_status'] == 'overdue']

    return calibration_report, overdue_devices


async def create_pivot_table_async(df: pd.DataFrame) -> tuple:
    """Создание сводных таблиц.

    Args:
        df: DataFrame.

    Returns:
        Кортеж из четырёх DataFrame:
        - pivot_clinic;
        - pivot_model;
        - device_table;
        - pivot_matrix.
    """
    await asyncio.sleep(0)
    pivot_clinic = df.groupby(['clinic_id', 'clinic_name', 'city']).agg({
        'device_id': 'count', 'issues_reported_12mo': 'sum',
        'failure_count_12mo': 'sum', 'uptime_pct': 'mean', 'model': 'nunique'
    }).reset_index()

    pivot_model = df.groupby(['model']).agg({
        'device_id': 'count', 'clinic_id': 'nunique',
        'issues_reported_12mo': 'sum', 'failure_count_12mo': 'sum',
        'uptime_pct': 'mean', 'warranty_expired': 'sum'
    }).reset_index()

    device_table = df[['device_id', 'clinic_id', 'clinic_name', 'city', 'department',
                       'model', 'serial_number', 'install_date_parsed', 'status_normalized',
                       'warranty_until_parsed', 'last_calibration_date_parsed',
                       'last_service_date_parsed', 'issues_reported_12mo',
                       'failure_count_12mo', 'uptime_pct', 'issues_text']]

    pivot_matrix = pd.pivot_table(
        df, values='device_id', index=['clinic_name', 'city'],
        columns=['model'], aggfunc='count', fill_value=0, margins=True
    )

    return pivot_clinic, pivot_model, device_table, pivot_matrix


async def df_to_devices_async(df: pd.DataFrame) -> List[MedicalDevice]:
    """Преобразование DataFrame в список объектов MedicalDevice.

    Args:
        df: DataFrame.

    Returns:
        Список объектов MedicalDevice.
    """

    devices = []

    for idx, row in df.iterrows():
        device = MedicalDevice(
            device_id=str(row.get('device_id', '')),
            clinic_id=str(row.get('clinic_id', '')),
            clinic_name=str(row.get('clinic_name', '')),
            city=str(row.get('city', '')),
            department=str(row.get('department', '')),
            model=str(row.get('model', '')),
            serial_number=str(row.get('serial_number', '')),
            install_date=pd.to_datetime(row.get('install_date'), errors='coerce'),
            warranty_until=pd.to_datetime(row.get('warranty_until'), errors='coerce'),
            last_calibration_date=pd.to_datetime(row.get('last_calibration_date'), errors='coerce'),
            last_service_date=pd.to_datetime(row.get('last_service_date'), errors='coerce'),
            status=str(row.get('status', 'unknown')),
            status_normalized=str(row.get('status_normalized', 'unknown')),
            issues_reported_12mo=int(row.get('issues_reported_12mo', 0) or 0),
            failure_count_12mo=int(row.get('failure_count_12mo', 0) or 0),
            uptime_pct=float(row.get('uptime_pct', 100.0) or 100.0),
            issues_text=str(row.get('issues_text', '')) if pd.notna(row.get('issues_text')) else None
        )
        devices.append(device)
        await asyncio.sleep(0)

    print(f"Создано объектов MedicalDevice: {len(devices)}")

    return devices


async def export_to_excel_async(data_dict: dict, filepath: str):
    """Экспорт всех результатов в Excel.

    Args:
        data_dict: Словарь с DataFrames для экспорта.
        filepath: Путь для сохранения файла.
    """
    await asyncio.sleep(0)
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        for sheet_name, df in data_dict.items():
            if isinstance(df, pd.DataFrame):
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                df.to_excel(writer, sheet_name=sheet_name)
    print(f"Сохранено в {filepath}")


async def run_analysis_async(folder_path: str) -> dict:
    """Главная функция анализа (асинхронная).

    Args:
        folder_path: Путь к папке с Excel файлами.

    Returns:
        Словарь с результатами анализа, содержащий:
            - processed_df: Обработанный DataFrame с данными
            - warranty_df: DataFrame с устройствами на гарантии
            - top_clinics: DataFrame с топ-5 проблемных клиник
            - calibration_report: DataFrame с отчётом по калибровке
            - overdue_devices: DataFrame с просроченной калибровкой
            - devices: Список объектов MedicalDevice
    """
    df = await load_all_files_async(folder_path)

    # Параллельная обработка
    df_normalized, df_processed = await asyncio.gather(
        normalize_status_async(df),
        process_data_async(df)
    )
    df = df_processed
    df['status_normalized'] = df_normalized['status_normalized']

    top_clinics, calibration_data, pivot_data = await asyncio.gather(
        analyze_clinics_async(df),
        generate_calibration_report_async(df),
        create_pivot_table_async(df)
    )

    calibration_report, overdue_devices = calibration_data
    pivot_clinic, pivot_model, device_table, pivot_matrix = pivot_data

    # Фильтрация и создание объектов
    df_warranty = await filter_by_warranty_async(df)
    devices = await df_to_devices_async(df)

    await export_to_excel_async({
        'raw_data': df,
        'top_clinics': top_clinics,
        'calibration_report': calibration_report,
        'overdue_devices': overdue_devices,
        'by_clinic': pivot_clinic,
        'by_model': pivot_model,
        'device_details': device_table,
        'clinic_model_matrix': pivot_matrix
    }, 'medical_devices_report_async.xlsx')

    print(f"\nВсего устройств: {len(df)}")
    print(f"Клиник: {df['clinic_id'].nunique()}")
    print(f"Устройств на гарантии: {len(df_warranty)}")
    print(f"Просроченная калибровка: {len(overdue_devices)}")
    print("\nТоп-5 проблемных клиник:")
    print(top_clinics[['clinic_name', 'city', 'problem_score']].head())

    return {
        'processed_df': df,
        'warranty_df': df_warranty,
        'top_clinics': top_clinics,
        'calibration_report': calibration_report,
        'overdue_devices': overdue_devices,
        'devices': devices
    }


if __name__ == '__main__':
    folder_path = 'C:/Users/admin/Desktop/медицина'


    print("Сравнение синхронной и асинхронной версии:")


    start_sync = time.time()
    results_sync = run_analysis_sync(folder_path)
    end_sync = time.time()
    time_sync = end_sync - start_sync
    print(f"Время выполнения (синхронно): {time_sync:.2f} секунд")

    start_async = time.time()
    results_async = asyncio.run(run_analysis_async(folder_path))
    end_async = time.time()
    time_async = end_async - start_async
    print(f"Время выполнения (асинхронно): {time_async:.2f} секунд")

    print(f"Синхронная версия:  {time_sync:.2f} сек")
    print(f"Асинхронная версия: {time_async:.2f} сек")

    if time_sync < time_async:
        print(f"Синхронная версия быстрее на {time_async - time_sync:.2f} сек")
    else:
        print(f"Асинхронная версия быстрее на {time_sync - time_async:.2f} сек")
