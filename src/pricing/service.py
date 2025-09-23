import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from ..pricing.model import PricingInput, PricingOutput
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PricingContext:
    """Context object containing all information needed for pricing calculation"""
    customer_code: str
    item_code: str
    quantity: Decimal
    currency: str = 'CRC'
    unit_of_measure: str = 'UN'
    site: str = ''
    sales_rep: str = ''
    order_date: datetime = None # type: ignore
    customer_category: str = ''
    item_category: str = ''
    
    def __post_init__(self):
        if self.order_date is None:
            self.order_date = datetime.now()





@dataclass
class PriceAdjustment:
    """Represents a single price adjustment (discount or fee) with complete Sage X3 semantics"""
    index: int
    value: Decimal
    adjustment_type: str  # 'discount' (minoration) or 'fee' (majoration)
    calculation_type: str  # 'amount', 'percentage_cumulative', 'percentage_cascading'
    calculation_basis: str  # 'unit', 'line', 'document'
    description: str = ''
    
    # Internal fields for calculation
    incdcr_flag: str = '0'  # Original INCDCR value
    valtyp_flag: str = '0'  # Original VALTYP value  
    clcrul_flag: str = '0'  # Original CLCRUL value

@dataclass
class PricingResult:
    """Result object containing calculated pricing information"""
    unit_price: Decimal = Decimal('0')
    base_price: Decimal = Decimal('0')  # Price before adjustments
    adjustments: List[PriceAdjustment] = None  # type: ignore # All adjustments (discounts + fees)
    free_items: List[Dict[str, Any]] = None # type: ignore
    commission_coefficient: Decimal = Decimal('1')
    pricing_rule_code: str = ''
    reason_code: str = ''
    currency: str = ''
    unit_of_measure: str = ''
    price_structure_code: str = ''  # The structure code used
    
    def __post_init__(self):
        if self.adjustments is None:
            self.adjustments = []
        if self.free_items is None:
            self.free_items = []
    
    @property
    def discounts(self) -> List[PriceAdjustment]:
        """Get only discount adjustments for backward compatibility"""
        return [adj for adj in self.adjustments if adj.adjustment_type == 'discount']
    
    @property
    def fees(self) -> List[PriceAdjustment]:
        """Get only fee adjustments"""
        return [adj for adj in self.adjustments if adj.adjustment_type == 'fee']

class SageX3PricingEngine:
    """
    Complete Sage X3 Pricing Engine Implementation
    
    This class implements the full Sage X3 pricing algorithm including proper handling 
    of discounts and fees based on the PRICSTRUCT table configuration with correct
    interpretation of INCDCR, VALTYP, and CLCRUL fields.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize the pricing engine with database connection
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.connection = None
        self._price_structures_cache = {}  # Cache for price structures
        
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            logger.info(f"Connected to database: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
    
    def get_price_structure(self, structure_code: str) -> Dict[int, Dict[str, str]]:
        """
        Get price structure configuration from PRICSTRUCT table
        
        This method retrieves the configuration that determines how each discount/fee
        column (DCGVAL_0 to DCGVAL_8) should be interpreted.
        
        Args:
            structure_code: The price structure code to look up
            
        Returns:
            Dictionary mapping column index to configuration:
            {
                0: {
                    'incdcr': '2',      # 1=Fee(Majoration), 2=Discount(Minoration), 0=Not used
                    'valtyp': '2',      # 1=Amount, 2=Cumulative%, 3=Cascading%, 0=Not used  
                    'clcrul': '1',      # 1=Per Unit, 2=Per Line, 3=Per Document, 0=Not used
                    'description': 'Discount 1'
                },
                ...
            }
        """
        # Check cache first
        if structure_code in self._price_structures_cache:
            return self._price_structures_cache[structure_code]
        
        cursor = self.connection.cursor() # type: ignore
        
        # Query to get the price structure configuration
        query = """
        SELECT * FROM PRICSTRUCT 
        WHERE PLISTC_0 = ?
        """
        
        cursor.execute(query, (structure_code,))
        result = cursor.fetchone()
        
        structure_config = {}
        
        if result:
            row_dict = dict(result)
            
            # Process each of the 9 discount/fee columns (0-8)
            for i in range(9):
                incdcr_field = f'INCDCR_{i}'
                valtyp_field = f'VALTYP_{i}'
                clcrul_field = f'CLCRUL_{i}'
                landessho_field = f'LANDESSHO_{i}'
                
                incdcr = row_dict.get(incdcr_field, '0')
                valtyp = row_dict.get(valtyp_field, '0')
                clcrul = row_dict.get(clcrul_field, '0')
                description = row_dict.get(landessho_field, f'Adjustment {i}')
                
                # Only include columns that are actually configured (not '0')
                if incdcr != '0' and valtyp != '0' and clcrul != '0':
                    structure_config[i] = {
                        'incdcr': incdcr,
                        'valtyp': valtyp,
                        'clcrul': clcrul,
                        'description': description
                    }
                    
                    logger.debug(f"Structure {structure_code} column {i}: "
                               f"INCDCR={incdcr}, VALTYP={valtyp}, CLCRUL={clcrul}")
        
        # Cache the result
        self._price_structures_cache[structure_code] = structure_config
        
        logger.info(f"Loaded price structure '{structure_code}' with {len(structure_config)} configured columns")
        return structure_config
    
    def get_pricing_configurations(self) -> List[Dict[str, Any]]:
        """
        Get all pricing configurations ordered by priority
        
        Returns:
            List of pricing configuration dictionaries
        """
        cursor = self.connection.cursor() # type: ignore
        
        query = """
        SELECT * FROM SPRICCONF 
        WHERE PLIENAFLG_0 = '2'  -- Active pricing rules
        ORDER BY PIO_0 ASC  -- Priority order (ascending)
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        configs = []
        for row in results:
            config = dict(row)
            logger.debug(f"Found pricing config: {config['PLI_0']} with priority {config['PIO_0']}")
            configs.append(config)
        
        return configs
    
    def build_pricing_criteria(self, context: PricingContext, config: Dict[str, Any]) -> Dict[str, str]:
        """
        Build pricing criteria based on the context and configuration
        
        Args:
            context: Pricing context
            config: Pricing configuration
            
        Returns:
            Dictionary of criteria values
        """
        criteria = {}
        
        # Extract criteria fields from configuration
        for i in range(5):  # Up to 5 criteria fields (PLICRI1_0 to PLICRI5_0)
            field_name = f'FLD_{i}'
            table_name = f'FIL_{i}'
            
            if field_name in config and config[field_name]:
                table = config[table_name]
                field = config[field_name]
                
                # Map the field to context value
                if table == 'ITMMASTER' and field == 'ITMREF':
                    criteria[f'PLICRI{i+1}_0'] = context.item_code
                elif table == 'BPCUSTOMER' and field == 'BPCNUM':
                    criteria[f'PLICRI{i+1}_0'] = context.customer_code
                elif table == 'SPRICLINK' and field == 'CUR':
                    criteria[f'PLICRI{i+1}_0'] = context.currency
                elif table == 'SPRICLINK' and field == 'UOM':
                    criteria[f'PLICRI{i+1}_0'] = context.unit_of_measure
                else:
                    criteria[f'PLICRI{i+1}_0'] = ''
        
        return criteria
    
    def find_applicable_pricing_lines(self, context: PricingContext, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find all pricing lines that match the given context and configuration
        
        Args:
            context: Pricing context
            config: Pricing configuration
            
        Returns:
            List of applicable pricing line dictionaries
        """
        cursor = self.connection.cursor() # type: ignore
        
        # Build criteria for matching
        criteria = self.build_pricing_criteria(context, config)
        
        # Build the WHERE clause based on criteria
        where_conditions = []
        params = []
        
        # Match pricing list code
        where_conditions.append("PLI_0 = ?")
        params.append(config['PLI_0'])
        
        # Match date range
        current_date = context.order_date.strftime('%Y-%m-%d %H:%M:%S')
        where_conditions.append("PLISTRDAT_0 <= ?")
        where_conditions.append("PLIENDDAT_0 >= ?")
        params.extend([current_date, current_date])
        
        # Match criteria fields
        for i in range(1, 6):
            criteria_field = f'PLICRI{i}_0'
            if criteria_field in criteria and criteria[criteria_field]:
                # Handle wildcard matching (~ characters in Sage X3)
                where_conditions.append(f"({criteria_field} = ? OR {criteria_field} LIKE '%~%')")
                params.append(criteria[criteria_field])
        
        # Match quantity range
        where_conditions.append("(MINQTY_0 <= ? OR MINQTY_0 = 0)")
        where_conditions.append("(MAXQTY_0 >= ? OR MAXQTY_0 = 0)")
        params.extend([float(context.quantity), float(context.quantity)])
        
        # Match currency
        where_conditions.append("CUR_0 = ?")
        params.append(context.currency)
        
        # Match unit of measure
        where_conditions.append("UOM_0 = ?")
        params.append(context.unit_of_measure)

        # print("Where conditions,", where_conditions)
        
        query = f"""
        SELECT * FROM SPRICLIST 
        WHERE {' AND '.join(where_conditions)}
        ORDER BY PLILIN_0 ASC
        """
        # print(f"Executing pricing query: {query}")
        # print(f"Query parameters: {params}")
        logger.debug(f"Executing pricing query: {query}")
        logger.debug(f"Query parameters: {params}")
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        applicable_lines = []
        for row in results:
            line = dict(row)
            logger.debug(f"Found applicable pricing line: {line['PLICRD_0']}")
            applicable_lines.append(line)
        
        return applicable_lines
    
    def calculate_price_from_line(self, context: PricingContext, line: Dict[str, Any], config: Dict[str, Any]) -> Decimal:
        """
        Calculate the base price from a specific pricing line
        
        Args:
            context: Pricing context
            line: Pricing line dictionary
            config: Pricing configuration
            
        Returns:
            Calculated price as Decimal
        """
        price_treatment = config.get('PRIPRO_0', '2')  # Default to 'Value'
        
        if price_treatment == '2':  # Value
            return Decimal(str(line.get('PRI_0', '0')))
        
        elif price_treatment == '1':  # Coefficient
            # Get base price field
            base_price_field = config.get('PRIFLD_0', '')
            if base_price_field:
                # This would require fetching from the referenced table/field
                # For now, using a default base price
                base_price = self.get_base_price(context.item_code)
                coefficient = Decimal(str(line.get('PRI_0', '1')))
                return base_price * coefficient
            
        elif price_treatment == '3':  # Calculation
            # This would require parsing and evaluating the formula
            # For now, return the direct price
            return Decimal(str(line.get('PRI_0', '0')))
        
        return Decimal('0')
    
    def get_base_price(self, item_code: str) -> Decimal:
        """
        Get the base price for an item from ITMMASTER table
        
        Args:
            item_code: Item reference code
            
        Returns:
            Base price as Decimal
        """
        cursor = self.connection.cursor() # type: ignore
        
        query = "SELECT BASPRI_0 FROM ITMMASTER WHERE ITMREF_0 = ?"
        cursor.execute(query, (item_code,))
        result = cursor.fetchone()
        
        if result:
            return Decimal(str(result['BASPRI_0']))
        
        return Decimal('0')
    
    def calculate_adjustments(self, context: PricingContext, line: Dict[str, Any], 
                            price_structure: Dict[int, Dict[str, str]]) -> List[PriceAdjustment]:
        """
        Calculate all price adjustments (discounts and fees) from a pricing line
        using the proper PRICSTRUCT interpretation
        
        Args:
            context: Pricing context
            line: Pricing line dictionary
            price_structure: Price structure configuration from PRICSTRUCT table
            
        Returns:
            List of PriceAdjustment objects with correct Sage X3 semantics
        """
        adjustments = []
        
        # Process adjustment values (DCGVAL_0 to DCGVAL_8)
        for i in range(9):
            dcgval_field = f'DCGVAL_{i}'
            
            # Check if there's a value to process
            if dcgval_field in line and line[dcgval_field] != '0.0':
                adjustment_value = Decimal(str(line[dcgval_field]))
                
                if adjustment_value != 0:
                    # Get the structure configuration for this column
                    if i in price_structure:
                        struct_config = price_structure[i]
                        
                        # Determine adjustment type based on INCDCR field
                        incdcr = struct_config['incdcr']
                        if incdcr == '1':  # Majoration (Fee/Charge)
                            adjustment_type = 'fee'
                        elif incdcr == '2':  # Minoration (Discount)
                            adjustment_type = 'discount'
                        else:
                            continue  # Skip if not properly configured
                        
                        # Determine calculation type based on VALTYP field
                        valtyp = struct_config['valtyp']
                        if valtyp == '1':  # Montant (Fixed Amount)
                            calculation_type = 'amount'
                        elif valtyp == '2':  # Pourcentage Cumulé (Cumulative Percentage)
                            calculation_type = 'percentage_cumulative'
                        elif valtyp == '3':  # Pourcentage Cascade (Cascading Percentage)
                            calculation_type = 'percentage_cascading'
                        else:
                            continue  # Skip if not properly configured
                        
                        # Determine calculation basis based on CLCRUL field
                        clcrul = struct_config['clcrul']
                        if clcrul == '1':  # Par Unité (Per Unit)
                            calculation_basis = 'unit'
                        elif clcrul == '2':  # Par Ligne (Per Line)
                            calculation_basis = 'line'
                        elif clcrul == '3':  # Par Document (Per Document)
                            calculation_basis = 'document'
                        else:
                            continue  # Skip if not properly configured
                        
                        # Create the adjustment with complete information
                        adjustment = PriceAdjustment(
                            index=i,
                            value=abs(adjustment_value),  # Always store as positive value
                            adjustment_type=adjustment_type,
                            calculation_type=calculation_type,
                            calculation_basis=calculation_basis,
                            description=struct_config.get('description', f'Adjustment {i}'),
                            incdcr_flag=incdcr,
                            valtyp_flag=valtyp,
                            clcrul_flag=clcrul
                        )
                        
                        adjustments.append(adjustment)
                        
                        logger.debug(f"Column {i}: {adjustment_type} {adjustment_value} "
                                   f"({calculation_type}, {calculation_basis}) - "
                                   f"INCDCR={incdcr}, VALTYP={valtyp}, CLCRUL={clcrul}")
                    else:
                        logger.debug(f"Column {i} has value {adjustment_value} but no structure configuration")
        
        return adjustments
    
    def calculate_free_items(self, context: PricingContext, line: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Calculate free items (gratuité) from a pricing line using complete Sage X3 logic
        
        Sage X3 Free Item Logic:
        - FOCPRO: Type of free item mechanism (Non, N pour M, Autre Article, Total Commande)
        - FOCTYP: How gratuity is attributed (Seuil, Multiple)
        - FOCQTYMIN/FOCAMTMIN: Minimum threshold to trigger free items
        - FOCQTYBKT/FOCAMTBKT: Bucket/tranche for multiple calculations
        - FOCITMREF: Free item reference (for "Autre Article" type)
        - FOCQTY: Free quantity per trigger
        
        Args:
            context: Pricing context
            line: Pricing line dictionary
            
        Returns:
            List of free item dictionaries
        """
        cursor = self.connection.cursor() # type: ignore

        query = f"""SELECT FOCPRO_0, FOCTYP_0 FROM SPRICCONF WHERE PLI_0 = ?"""
        cursor.execute(query, (line.get('PLI_0'),))
        result = cursor.fetchone()
        print( "configurations for free items", result['FOCPRO_0'] )
        free_items = []
        
        # Get free item configuration from the pricing line
        # focpro = line.get('FOCPRO_0', '0')  # Free item mechanism type
        focpro = result['FOCPRO_0']
        # print("lines = = = = >", line)
        print("Free items ====>", line.get('FOCPRO_0'))
        # foctyp = line.get('FOCTYP_0', '0')  # Attribution type (threshold vs multiple)
        foctyp = result['FOCTYP_0']
        focqtymin = Decimal(str(line.get('FOCQTYMIN_0', '0')))  # Quantity threshold
        focamtmin = Decimal(str(line.get('FOCAMTMIN_0', '0')))  # Amount threshold  
        focqtybkt = Decimal(str(line.get('FOCQTYBKT_0', '0')))  # Quantity bucket/tranche
        focamtbkt = Decimal(str(line.get('FOCAMTBKT_0', '0')))  # Amount bucket/tranche
        focitmref = line.get('FOCITMREF_0', '').strip()  # Free item reference
        focqty = Decimal(str(line.get('FOCQTY_0', '0')))  # Free quantity per trigger
        
        if focpro == '0' or focpro == '' or focqty <= 0:
            logger.debug("No free item configuration found or invalid")
            return free_items
            
        logger.info(f"Processing free items: FOCPRO={focpro}, FOCTYP={foctyp}")
        logger.debug(f"Thresholds: QtyMin={focqtymin}, AmtMin={focamtmin}")
        logger.debug(f"Buckets: QtyBkt={focqtybkt}, AmtBkt={focamtbkt}")
        logger.debug(f"Free item: {focitmref}, Free qty: {focqty}")
        
        # Calculate line amount for threshold checks
        line_amount = context.quantity * self.get_current_unit_price_for_free_calc(context, line)
        
        print(f"\n=== FREE ITEMS CALCULATION ===")
        print(f"Free item mechanism: {self.get_focpro_description(focpro)}")
        print(f"Attribution type: {self.get_foctyp_description(foctyp)}")
        print(f"Ordered quantity: {context.quantity}")
        print(f"Line amount: {line_amount} {context.currency}")
        print(f"Quantity threshold: {focqtymin}")
        print(f"Amount threshold: {focamtmin} {context.currency}")
        
        if focpro == '1':  # N pour M (same item free)
            free_items = self.calculate_n_for_m_free_items(
                context, foctyp, focqtymin, focqtybkt, focqty, line_amount, focamtmin, focamtbkt
            )
            
        elif focpro == '2':  # Autre Article (different item free)  
            if not focitmref:
                logger.warning("FOCPRO=2 (Autre Article) but no FOCITMREF specified")
                return free_items
                
            free_items = self.calculate_other_item_free_items(
                context, foctyp, focqtymin, focqtybkt, focitmref, focqty, 
                line_amount, focamtmin, focamtbkt
            )
            
        elif focpro == '3':  # Total Commande (order total based)
            # This would require full order context, approximating with current line
            logger.warning("FOCPRO=3 (Total Commande) approximated as single line")
            free_items = self.calculate_order_total_free_items(
                context, foctyp, focqtymin, focqtybkt, focitmref, focqty,
                line_amount, focamtmin, focamtbkt
            )
        
        if free_items:
            print(f"FREE ITEMS AWARDED:")
            for item in free_items:
                print(f"  * {item['item_code']}: {item['quantity']} {item['unit_of_measure']}")
        else:
            print("No free items awarded (threshold not met)")
        print("=" * 40)
        
        return free_items
    
    def get_focpro_description(self, focpro: str) -> str:
        """Get description for FOCPRO value"""
        descriptions = {
            '0': 'None (No free items)',
            '1': 'N pour M (Same item free)', 
            '2': 'Autre Article (Different item free)',
            '3': 'Total Commande (Order total based)'
        }
        return descriptions.get(focpro, f'Unknown ({focpro})')
    
    def get_foctyp_description(self, foctyp: str) -> str:
        """Get description for FOCTYP value"""
        descriptions = {
            '0': 'None',
            '1': 'Seuil (Threshold - one-time when reached)',
            '2': 'Multiple (Multiple - by buckets beyond threshold)'
        }
        return descriptions.get(foctyp, f'Unknown ({foctyp})')
    
    def get_current_unit_price_for_free_calc(self, context: PricingContext, line: Dict[str, Any]) -> Decimal:
        """
        Get current unit price for free item calculations
        This should use the base price before adjustments for consistency
        """
        return Decimal(str(line.get('PRI_0', '0')))
    
    def calculate_n_for_m_free_items(self, context: PricingContext, foctyp: str, 
                                   focqtymin: Decimal, focqtybkt: Decimal, focqty: Decimal,
                                   line_amount: Decimal, focamtmin: Decimal, focamtbkt: Decimal) -> List[Dict[str, Any]]:
        """
        Calculate free items for "N pour M" (same item free) scenario
        """
        free_items = []
        free_quantity = Decimal('0')
        
        # Determine if we use quantity or amount based threshold
        use_quantity_threshold = focqtymin > 0
        use_amount_threshold = focamtmin > 0
        
        if use_quantity_threshold:
            print(f"Using QUANTITY threshold logic:")
            print(f"  Threshold: {focqtymin} units")
            
            if context.quantity >= focqtymin:
                if foctyp == '1':  # Seuil (threshold - one time)
                    free_quantity = focqty
                    print(f"  Threshold reached → {focqty} free items awarded (one-time)")
                    
                elif foctyp == '2':  # Multiple (by buckets)
                    if focqtybkt > 0:
                        excess_qty = context.quantity - focqtymin
                        buckets = (excess_qty / focqtybkt).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                        free_quantity = buckets * focqty
                        print(f"  Excess quantity: {excess_qty}")
                        print(f"  Buckets of {focqtybkt}: {buckets}")
                        print(f"  Free items: {buckets} × {focqty} = {free_quantity}")
                    else:
                        logger.warning("FOCTYP=2 but FOCQTYBKT=0, cannot calculate buckets")
            else:
                print(f"  Quantity {context.quantity} < threshold {focqtymin}, no free items")
        
        elif use_amount_threshold:
            print(f"Using AMOUNT threshold logic:")  
            print(f"  Threshold: {focamtmin} {context.currency}")
            
            if line_amount >= focamtmin:
                if foctyp == '1':  # Seuil (threshold - one time)
                    free_quantity = focqty
                    print(f"  Threshold reached → {focqty} free items awarded (one-time)")
                    
                elif foctyp == '2':  # Multiple (by buckets)
                    if focamtbkt > 0:
                        excess_amt = line_amount - focamtmin
                        buckets = (excess_amt / focamtbkt).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                        free_quantity = buckets * focqty
                        print(f"  Excess amount: {excess_amt} {context.currency}")
                        print(f"  Buckets of {focamtbkt}: {buckets}")
                        print(f"  Free items: {buckets} × {focqty} = {free_quantity}")
                    else:
                        logger.warning("FOCTYP=2 but FOCAMTBKT=0, cannot calculate buckets")
            else:
                print(f"  Amount {line_amount} < threshold {focamtmin}, no free items")
        
        if free_quantity > 0:
            free_items.append({
                'item_code': context.item_code,  # Same item
                'quantity': free_quantity,
                'unit_of_measure': context.unit_of_measure,
                'free_type': 'N pour M'
            })
            
        return free_items
    
    def calculate_other_item_free_items(self, context: PricingContext, foctyp: str,
                                      focqtymin: Decimal, focqtybkt: Decimal, focitmref: str, focqty: Decimal,
                                      line_amount: Decimal, focamtmin: Decimal, focamtbkt: Decimal) -> List[Dict[str, Any]]:
        """
        Calculate free items for "Autre Article" (different item free) scenario
        """
        free_items = []
        free_quantity = Decimal('0')
        
        # Determine if we use quantity or amount based threshold
        use_quantity_threshold = focqtymin > 0
        use_amount_threshold = focamtmin > 0
        
        if use_quantity_threshold:
            print(f"Using QUANTITY threshold for other item ({focitmref}):")
            print(f"  Threshold: {focqtymin} units")
            
            if context.quantity >= focqtymin:
                if foctyp == '1':  # Seuil (threshold - one time)
                    free_quantity = focqty
                    print(f"  Threshold reached → {focqty} of {focitmref} awarded (one-time)")
                    
                elif foctyp == '2':  # Multiple (by buckets)
                    if focqtybkt > 0:
                        buckets = (context.quantity / focqtybkt).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                        free_quantity = buckets * focqty
                        print(f"  Buckets of {focqtybkt}: {buckets}")
                        print(f"  Free items: {buckets} × {focqty} = {free_quantity} of {focitmref}")
                    else:
                        logger.warning("FOCTYP=2 but FOCQTYBKT=0, cannot calculate buckets")
        
        elif use_amount_threshold:
            print(f"Using AMOUNT threshold for other item ({focitmref}):")
            print(f"  Threshold: {focamtmin} {context.currency}")
            
            if line_amount >= focamtmin:
                if foctyp == '1':  # Seuil (threshold - one time)  
                    free_quantity = focqty
                    print(f"  Threshold reached → {focqty} of {focitmref} awarded (one-time)")
                    
                elif foctyp == '2':  # Multiple (by buckets)
                    if focamtbkt > 0:
                        buckets = (line_amount / focamtbkt).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                        free_quantity = buckets * focqty
                        print(f"  Buckets of {focamtbkt}: {buckets}")
                        print(f"  Free items: {buckets} × {focqty} = {free_quantity} of {focitmref}")
                    else:
                        logger.warning("FOCTYP=2 but FOCAMTBKT=0, cannot calculate buckets")
        
        if free_quantity > 0:
            free_items.append({
                'item_code': focitmref,  # Different item
                'quantity': free_quantity,
                'unit_of_measure': context.unit_of_measure,  # Assume same UOM, could be configurable
                'free_type': 'Autre Article'
            })
            
        return free_items
    
    def calculate_order_total_free_items(self, context: PricingContext, foctyp: str,
                                       focqtymin: Decimal, focqtybkt: Decimal, focitmref: str, focqty: Decimal,
                                       line_amount: Decimal, focamtmin: Decimal, focamtbkt: Decimal) -> List[Dict[str, Any]]:
        """
        Calculate free items for "Total Commande" (order total based) scenario
        Note: This is approximated for single line context
        """
        free_items = []
        
        # In a real implementation, this would need full order context
        # For now, we approximate using the current line totals
        logger.warning("Order total free items approximated using current line only")
        
        print(f"Using ORDER TOTAL logic (approximated as line total):")
        
        # Use the "Autre Article" logic but with order total context
        if focitmref:
            free_items = self.calculate_other_item_free_items(
                context, foctyp, focqtymin, focqtybkt, focitmref, focqty,
                line_amount, focamtmin, focamtbkt
            )
        else:
            # If no specific item reference, use same item
            free_items = self.calculate_n_for_m_free_items(
                context, foctyp, focqtymin, focqtybkt, focqty,
                line_amount, focamtmin, focamtbkt
            )
            
        # Mark as order total type
        for item in free_items:
            item['free_type'] = 'Total Commande (approximated)'
            
        return free_items
    
    def calculate_pricing(self, context: PricingContext) -> PricingResult:
        """
        Main pricing calculation method with complete Sage X3 semantics
        
        This method follows the exact Sage X3 pricing algorithm:
        1. Find applicable pricing configurations by priority
        2. For each configuration, find matching pricing lines  
        3. Apply the first matching line's pricing rules
        4. Use PRICSTRUCT to interpret discount/fee columns correctly
        5. Apply adjustments in the correct order with proper calculation types
        
        Args:
            context: Pricing context containing all necessary information
            
        Returns:
            PricingResult object with calculated pricing information
        """
        logger.info(f"Starting pricing calculation for item: {context.item_code}, customer: {context.customer_code}")
        
        result = PricingResult()
        result.currency = context.currency
        result.unit_of_measure = context.unit_of_measure
        
        # Get all pricing configurations ordered by priority
        configs = self.get_pricing_configurations()
        
        if not configs:
            logger.warning("No pricing configurations found")
            return result
        
        # Process each configuration by priority
        for config in configs:
            logger.debug(f"Processing pricing config: {config['PLI_0']} (priority: {config['PIO_0']})")
            
            # Find applicable pricing lines
            applicable_lines = self.find_applicable_pricing_lines(context, config)
            
            if not applicable_lines:
                logger.debug(f"No applicable lines found for config: {config['PLI_0']}")
                continue
            
            # Process the first applicable line (they are ordered by PLILIN_0)
            line = applicable_lines[0]
            
            logger.info(f"Applying pricing line: {line['PLICRD_0']} from config: {config['PLI_0']}")
            
            # Calculate base price
            base_price = self.calculate_price_from_line(context, line, config)
            if base_price > 0:
                result.base_price = base_price
                result.unit_price = base_price  # Will be adjusted later
                result.pricing_rule_code = config['PLI_0']
                result.reason_code = config.get('PLISTC_0', '')
                result.price_structure_code = config.get('PLISTC_0', '')
                
                logger.debug(f"Base price calculated: {base_price}")
            
            # Get the price structure configuration for this pricing rule
            structure_code = config.get('PLISTC_0', '')
            price_structure = {}
            
            if structure_code:
                price_structure = self.get_price_structure(structure_code)
                logger.debug(f"Using price structure: {structure_code}")
            
            # Calculate adjustments using the price structure
            adjustments = self.calculate_adjustments(context, line, price_structure)
            result.adjustments.extend(adjustments)
            
            # Calculate free items (gratuitÃ©)
            free_items = self.calculate_free_items(context, line)
            result.free_items.extend(free_items)
            
            # Commission coefficient
            if line.get('COMCOE_0'):
                result.commission_coefficient = Decimal(str(line['COMCOE_0']))
            
            # For normal pricing (PLITYP_0 = '1'), we can apply multiple rules
            # For grouped pricing (PLITYP_0 = '2'), we stop at the first applicable rule
            if config.get('PLITYP_0') == '2':  # Grouped pricing
                logger.info("Grouped pricing applied, stopping rule processing")
                break
        
        # Apply all adjustments using proper Sage X3 calculation methods
        result.unit_price = self.apply_sage_x3_adjustments(result.base_price, result.adjustments, context)
        
        # Apply currency conversion if needed
        result = self.apply_currency_conversion(result, context)
        
        # Apply unit conversion if needed
        result = self.apply_unit_conversion(result, context)
        
        logger.info(f"Pricing calculation completed. Base price: {result.base_price}, "
                   f"Final price after adjustments: {result.unit_price} {result.currency}")
        
        return result
    
    def apply_sage_x3_adjustments(self, base_price: Decimal, adjustments: List[PriceAdjustment], 
                                  context: PricingContext) -> Decimal:
        """
        Apply all adjustments using proper Sage X3 calculation methods
        
        This method handles the different calculation bases correctly:
        - Par Unité (CLCRUL=1): Applied directly to unit price
        - Par Ligne (CLCRUL=2): Applied to line total, then distributed back to unit price  
        - Par Document (CLCRUL=3): Applied to document total (approximated as line total)
        
        And the different percentage calculation types correctly:
        - Cumulative percentages are applied to the running total
        - Cascading percentages are always applied to the original base price/total
        - Fixed amounts are applied directly
        
        Args:
            base_price: The original unit price before adjustments
            adjustments: List of PriceAdjustment objects
            context: Pricing context for line/document calculations
            
        Returns:
            Final unit price after all adjustments have been applied
        """
        if not adjustments or base_price == 0:
            return base_price
        
        # Sort adjustments by index to ensure consistent application order
        sorted_adjustments = sorted(adjustments, key=lambda adj: adj.index)
        
        current_unit_price = base_price
        original_base_price = base_price
        original_line_total = base_price * context.quantity
        current_line_total = original_line_total
        
        total_unit_discounts = Decimal('0')
        total_unit_fees = Decimal('0')
        total_line_discounts = Decimal('0')
        total_line_fees = Decimal('0')
        
        print(f"\n=== SAGE X3 ADJUSTMENT CALCULATION DETAILS ===")
        print(f"Base unit price: {base_price} {context.currency}")
        print(f"Quantity: {context.quantity}")
        print(f"Original line total: {original_line_total} {context.currency}")
        print(f"Processing {len(sorted_adjustments)} adjustments in order:\n")

        
        
        logger.debug(f"Applying {len(sorted_adjustments)} adjustments to base price: {base_price}")
        logger.debug(f"Quantity: {context.quantity}, Original line total: {original_line_total}")
        
        for i, adjustment in enumerate(sorted_adjustments):
            print(f"--- Adjustment {i+1}: Column {adjustment.index} ---")
            print(f"Type: {adjustment.adjustment_type.upper()}")
            print(f"Description: {adjustment.description}")
            print(f"Value: {adjustment.value}")
            print(f"Calculation Type: {adjustment.calculation_type}")
            print(f"Calculation Basis: {adjustment.calculation_basis}")
            print(f"Flags: INCDCR={adjustment.incdcr_flag}, VALTYP={adjustment.valtyp_flag}, CLCRUL={adjustment.clcrul_flag}")
            
            adjustment_amount = Decimal('0')
            
            # Calculate adjustment amount based on basis (CLCRUL)
            if adjustment.calculation_basis == 'unit':  # CLCRUL=1 - Par Unité
                print(f"Applying to UNIT PRICE:")
                
                if adjustment.calculation_type == 'amount':
                    # Fixed amount per unit
                    adjustment_amount = adjustment.value
                    print(f"  Fixed amount per unit: {adjustment_amount} {context.currency}")
                    
                elif adjustment.calculation_type == 'percentage_cumulative':
                    # Percentage of current unit price
                    adjustment_amount = (current_unit_price * adjustment.value) / Decimal('100')
                    print(f"  Cumulative %: {current_unit_price} × {adjustment.value}% = {adjustment_amount} {context.currency}")
                    
                elif adjustment.calculation_type == 'percentage_cascading':
                    # Percentage of original unit price
                    adjustment_amount = (original_base_price * adjustment.value) / Decimal('100')
                    print(f"  Cascading %: {original_base_price} × {adjustment.value}% = {adjustment_amount} {context.currency}")
                
                # Apply to unit price
                if adjustment.adjustment_type == 'discount':
                    current_unit_price -= adjustment_amount
                    total_unit_discounts += adjustment_amount
                    print(f"  Unit price after discount: {current_unit_price} {context.currency}")
                else:  # fee
                    current_unit_price += adjustment_amount
                    total_unit_fees += adjustment_amount
                    print(f"  Unit price after fee: {current_unit_price} {context.currency}")
                
                # Update line total to reflect unit price change
                current_line_total = current_unit_price * context.quantity
                print(f"  New line total: {current_line_total} {context.currency}")
                
            elif adjustment.calculation_basis == 'line':  # CLCRUL=2 - Par Ligne
                print(f"Applying to LINE TOTAL:")
                
                if adjustment.calculation_type == 'amount':
                    # Fixed amount for entire line (not per unit!)
                    adjustment_amount = adjustment.value
                    print(f"  Fixed amount for entire line: {adjustment_amount} {context.currency}")
                    
                elif adjustment.calculation_type == 'percentage_cumulative':
                    # Percentage of current line total
                    adjustment_amount = (current_line_total * adjustment.value) / Decimal('100')
                    print(f"  Cumulative %: {current_line_total} × {adjustment.value}% = {adjustment_amount} {context.currency}")
                    
                elif adjustment.calculation_type == 'percentage_cascading':
                    # Percentage of original line total (ALWAYS original, not current)
                    adjustment_amount = (original_line_total * adjustment.value) / Decimal('100')
                    print(f"  Cascading %: {original_line_total} × {adjustment.value}% = {adjustment_amount} {context.currency}")
                
                # Apply to line total
                if adjustment.adjustment_type == 'discount':
                    current_line_total -= adjustment_amount
                    total_line_discounts += adjustment_amount
                    print(f"  Line total after discount: {current_line_total} {context.currency}")
                else:  # fee
                    current_line_total += adjustment_amount
                    total_line_fees += adjustment_amount
                    print(f"  Line total after fee: {current_line_total} {context.currency}")
                
                # Update unit price to reflect line total change
                current_unit_price = current_line_total / context.quantity
                print(f"  Impact on unit price: {current_line_total} ÷ {context.quantity} = {current_unit_price} {context.currency}")
                
            elif adjustment.calculation_basis == 'document':  # CLCRUL=3 - Par Document
                print(f"Applying to DOCUMENT TOTAL (approximated as line total):")
                logger.warning("Document-level calculation approximated as line-level (single line context)")
                
                if adjustment.calculation_type == 'amount':
                    # Fixed amount for entire document
                    adjustment_amount = adjustment.value
                    print(f"  Fixed amount for entire document: {adjustment_amount} {context.currency}")
                    
                elif adjustment.calculation_type == 'percentage_cumulative':
                    # In real Sage X3, this would be % of current document total
                    adjustment_amount = (current_line_total * adjustment.value) / Decimal('100')
                    print(f"  Cumulative % (approx): {current_line_total} × {adjustment.value}% = {adjustment_amount} {context.currency}")
                    
                elif adjustment.calculation_type == 'percentage_cascading':
                    # In real Sage X3, this would be % of original document total
                    adjustment_amount = (original_line_total * adjustment.value) / Decimal('100')
                    print(f"  Cascading % (approx): {original_line_total} × {adjustment.value}% = {adjustment_amount} {context.currency}")
                
                # Apply to line total (approximating document total)
                if adjustment.adjustment_type == 'discount':
                    current_line_total -= adjustment_amount
                    total_line_discounts += adjustment_amount
                    print(f"  Line total after discount: {current_line_total} {context.currency}")
                else:  # fee
                    current_line_total += adjustment_amount
                    total_line_fees += adjustment_amount
                    print(f"  Line total after fee: {current_line_total} {context.currency}")
                
                # Update unit price to reflect line total change
                current_unit_price = current_line_total / context.quantity
                print(f"  Impact on unit price: {current_line_total} ÷ {context.quantity} = {current_unit_price} {context.currency}")
            
            print()  # Blank line for readability
        
        # Ensure price doesn't go negative
        if current_unit_price < 0:
            logger.warning(f"Price calculation resulted in negative value: {current_unit_price}, setting to 0")
            current_unit_price = Decimal('0')
        
        # Round to appropriate decimal places (typically 2 for currency)
        final_price = current_unit_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Summary
        print("=== ADJUSTMENT SUMMARY ===")
        print(f"Original unit price: {base_price} {context.currency}")
        if total_unit_discounts > 0:
            print(f"Total unit discounts: -{total_unit_discounts} {context.currency}")
        if total_unit_fees > 0:
            print(f"Total unit fees: +{total_unit_fees} {context.currency}")
        if total_line_discounts > 0:
            line_impact_per_unit = total_line_discounts / context.quantity
            print(f"Total line discounts: -{total_line_discounts} {context.currency} (impact per unit: -{line_impact_per_unit} {context.currency})")
        if total_line_fees > 0:
            line_impact_per_unit = total_line_fees / context.quantity
            print(f"Total line fees: +{total_line_fees} {context.currency} (impact per unit: +{line_impact_per_unit} {context.currency})")
        print(f"Final unit price: {final_price} {context.currency}")
        print(f"Final line total: {final_price * context.quantity} {context.currency}")
        print("=" * 50)
        
        logger.info(f"Sage X3 adjustment summary: Base price: {base_price}, "
                   f"Unit discounts: -{total_unit_discounts}, Unit fees: +{total_unit_fees}, "
                   f"Line discounts: -{total_line_discounts}, Line fees: +{total_line_fees}, "
                   f"Final unit price: {final_price}")
        logger.info(f"Final line total: {final_price * context.quantity}")
        
        return final_price
    
    def apply_currency_conversion(self, result: PricingResult, context: PricingContext) -> PricingResult:
        """
        Apply currency conversion if needed
        
        Args:
            result: Current pricing result
            context: Pricing context
            
        Returns:
            Updated pricing result
        """
        # Currency conversion logic would go here
        # For now, assuming no conversion is needed
        return result
    
    def apply_unit_conversion(self, result: PricingResult, context: PricingContext) -> PricingResult:
        """
        Apply unit of measure conversion if needed
        
        Args:
            result: Current pricing result
            context: Pricing context
            
        Returns:
            Updated pricing result
        """
        # Unit conversion logic would go here
        # For now, assuming no conversion is needed
        return result

# Utility functions for testing and demonstration
def create_sample_context(input: PricingInput) -> PricingContext:
    """Create a sample pricing context for testing"""
    return PricingContext(
        customer_code= input.customer_code,
        item_code= input.item_code,
        quantity= Decimal(input.quantity),
        currency= input.currency,
        unit_of_measure= input.unit_of_measure,
        order_date= input.order_date
    )

def create_sample_context_with_fees() -> PricingContext:
    """Create a sample context that might trigger both discounts and fees"""
    return PricingContext(
        customer_code="CUST002",
        item_code="BMS003", 
        quantity=Decimal("175"),
        currency="CRC",
        unit_of_measure="UN",
        order_date=datetime(2025, 8, 15)
    )

def test_calculation_types():
    """
    Test pour vérifier les différents types de calculs Sage X3
    """
    print("=== Test des Types de Calculs Sage X3 ===\n")
    
    # Prix de base: 100 EUR, Quantité: 10
    base_price = Decimal('100.00')
    quantity = Decimal('10')
    line_total = base_price * quantity  # 1000 EUR
    
    print(f"Prix de base: {base_price} EUR")
    print(f"Quantité: {quantity}")  
    print(f"Total ligne initial: {line_total} EUR\n")
    
    # Test 1: Remise 10% par unité (cumulé)
    print("Test 1: Remise 10% par unité (pourcentage cumulé)")
    discount_amount = (base_price * Decimal('10')) / Decimal('100')
    new_unit_price = base_price - discount_amount
    print(f"- Calcul: {base_price} - ({base_price} × 10%) = {new_unit_price} EUR/unité")
    print(f"- Nouveau total ligne: {new_unit_price * quantity} EUR\n")
    
    # Test 2: Frais 50 EUR par ligne (montant fixe)
    print("Test 2: Frais 50 EUR par ligne (montant fixe)")
    fee_per_line = Decimal('50.00')
    impact_per_unit = fee_per_line / quantity
    final_unit_price = new_unit_price + impact_per_unit
    print(f"- Frais total ligne: {fee_per_line} EUR")
    print(f"- Impact par unité: {fee_per_line} ÷ {quantity} = {impact_per_unit} EUR/unité")
    print(f"- Prix final par unité: {new_unit_price} + {impact_per_unit} = {final_unit_price} EUR")
    print(f"- Total ligne final: {final_unit_price * quantity} EUR\n")
    
    # Test 3: Comparaison avec frais par unité
    print("Test 3: Comparaison - Frais 50 EUR par unité (au lieu de par ligne)")
    fee_per_unit = Decimal('50.00')
    alt_final_price = new_unit_price + fee_per_unit
    print(f"- Prix final par unité: {new_unit_price} + {fee_per_unit} = {alt_final_price} EUR")
    print(f"- Total ligne final: {alt_final_price * quantity} EUR")
    print(f"- Différence avec 'par ligne': {(alt_final_price - final_unit_price) * quantity} EUR\n")
    
    # Test 4: Pourcentage cascading vs cumulé
    print("Test 4: Pourcentage Cascading vs Cumulé")
    print("Scénario: Prix 100, Remise1 10%, Remise2 5%")
    
    # Cumulé
    price_after_discount1 = Decimal('100') - (Decimal('100') * Decimal('10') / Decimal('100'))  # 90
    price_cumulative = price_after_discount1 - (price_after_discount1 * Decimal('5') / Decimal('100'))  # 85.5
    print(f"- Cumulé: 100 → 90 → {price_cumulative} EUR")
    
    # Cascade  
    discount1_cascade = (Decimal('100') * Decimal('10') / Decimal('100'))  # 10
    discount2_cascade = (Decimal('100') * Decimal('5') / Decimal('100'))   # 5 (toujours sur le prix original)
    price_cascade = Decimal('100') - discount1_cascade - discount2_cascade  # 85
    print(f"- Cascade: 100 - 10 - 5 = {price_cascade} EUR")
    print(f"- Différence: {price_cumulative - price_cascade} EUR")

def test_pricing_engine_complete(input_contexts: List[PricingInput]) -> List[PricingOutput]:
    """
    Complete test of the Sage X3 pricing engine showing the full breakdown
    
    Args:
        db_path: Path to the SQLite database
    """
    print("=== Complete Sage X3 Pricing Engine Test ===\n")
    db_path = "sagex3_seed.db"
    
    with SageX3PricingEngine(db_path) as engine:
        # Test multiple contexts
        output_result = []
        contexts = [
            ("Standard Context (150 units)", create_sample_context( 
                input= PricingInput(
                    customer_code=input_context.customer_code,
                    item_code=input_context.item_code,
                    quantity=input_context.quantity,
                    currency=input_context.currency,
                    unit_of_measure=input_context.unit_of_measure
                )
             )) for input_context in input_contexts
        ]

        
        for context_name, context in contexts:
            print(f"\n{'='*60}")
            print(f"TESTING: {context_name}")
            print(f"{'='*60}")
            print(f"- Customer: {context.customer_code}")
            print(f"- Item: {context.item_code}")
            print(f"- Quantity: {context.quantity}")
            print(f"- Currency: {context.currency}")
            print(f"- Unit: {context.unit_of_measure}")
            print(f"- Date: {context.order_date}")
            print()
            
            # Calculate pricing
            result = engine.calculate_pricing(context)
            
            print("\n=== PRICING CALCULATION RESULTS ===")
            print(f"- Pricing Rule Applied: {result.pricing_rule_code}")
            print(f"- Price Structure Used: {result.price_structure_code}")
            print(f"- Reason Code: {result.reason_code}")
            print()
            
            print("=== DETAILED PRICE BREAKDOWN ===")
            print(f"- Base Unit Price: {result.base_price} {result.currency}")
            
            # Show detailed adjustment breakdown
            if result.adjustments:
                print("- Applied Adjustments (by type):")
                
                # Group by type for clear display
                discounts = result.discounts
                fees = result.fees
                
                if discounts:
                    print("  DISCOUNTS (Minorations):")
                    for discount in discounts:
                        type_desc = {
                            'amount': 'Fixed Amount',
                            'percentage_cumulative': 'Cumulative %',
                            'percentage_cascading': 'Cascading %'
                        }.get(discount.calculation_type, discount.calculation_type)
                        
                        basis_desc = {
                            'unit': 'Per Unit',
                            'line': 'Per Line', 
                            'document': 'Per Document'
                        }.get(discount.calculation_basis, discount.calculation_basis)
                        
                        value_display = f"{discount.value}%" if 'percentage' in discount.calculation_type else f"{discount.value} {result.currency}"
                        
                        print(f"    * Column {discount.index} ({discount.description}): -{value_display}")
                        print(f"      Type: {type_desc}, Basis: {basis_desc}")
                        print(f"      SAGE X3 Flags: INCDCR={discount.incdcr_flag}, VALTYP={discount.valtyp_flag}, CLCRUL={discount.clcrul_flag}")
                
                if fees:
                    print("  FEES/CHARGES (Majorations):")
                    for fee in fees:
                        type_desc = {
                            'amount': 'Fixed Amount',
                            'percentage_cumulative': 'Cumulative %',
                            'percentage_cascading': 'Cascading %'
                        }.get(fee.calculation_type, fee.calculation_type)
                        
                        basis_desc = {
                            'unit': 'Per Unit',
                            'line': 'Per Line',
                            'document': 'Per Document'
                        }.get(fee.calculation_basis, fee.calculation_basis)
                        
                        value_display = f"{fee.value}%" if 'percentage' in fee.calculation_type else f"{fee.value} {result.currency}"
                        
                        print(f"    * Column {fee.index} ({fee.description}): +{value_display}")
                        print(f"      Type: {type_desc}, Basis: {basis_desc}")
                        print(f"      SAGE X3 Flags: INCDCR={fee.incdcr_flag}, VALTYP={fee.valtyp_flag}, CLCRUL={fee.clcrul_flag}")
                print()
            else:
                print("- No adjustments applied")
            
            print(f"- Final Unit Price: {result.unit_price} {result.currency}")
            print(f"- Commission Coefficient: {result.commission_coefficient}")
            
            # Show free items
            if result.free_items:
                print("=== FREE ITEMS AWARDED (Gratuités) ===")
                for free_item in result.free_items:
                    free_type = free_item.get('free_type', 'Unknown')
                    print(f"- {free_item['item_code']}: {free_item['quantity']} {free_item['unit_of_measure']}")
                    print(f"  Type: {free_type}")
                    
                    # Calculate value of free items if possible
                    if free_item['item_code'] == context.item_code:
                        # Same item - use calculated unit price
                        free_value = result.unit_price * free_item['quantity']
                        print(f"  Estimated value: {free_value} {result.currency}")
                print()
            else:
                print("- No free items awarded")
                print()
            
            # Calculate line totals for context
            line_total_before = result.base_price * context.quantity
            line_total_after = result.unit_price * context.quantity
            line_savings = line_total_before - line_total_after
            
            print(f"\n=== LINE TOTALS (Quantity: {context.quantity}) ===")
            print(f"- Before adjustments: {line_total_before} {result.currency}")
            print(f"- After adjustments: {line_total_after} {result.currency}")
            if line_savings > 0:
                print(f"- Total savings: {line_savings} {result.currency}")
                savings_percent = (line_savings / line_total_before) * 100
                print(f"- Savings percentage: {savings_percent.quantize(Decimal('0.01'))}%")
            elif line_savings < 0:
                print(f"- Additional charges: {abs(line_savings)} {result.currency}")
                charge_percent = (abs(line_savings) / line_total_before) * 100
                print(f"- Additional charge percentage: {charge_percent.quantize(Decimal('0.01'))}%")
            
            print(f"\n{'='*60}\n")
            output_result.append(PricingOutput(
                item_code=context.item_code,
            prix_brut=float(Decimal(line_total_before) / Decimal(context.quantity)),
            prix_net= float(Decimal(line_total_after) / Decimal(context.quantity)),
            total_HT=float(line_total_after),
            gratuit= result.free_items # type: ignore
        ))
        return output_result

def explain_sage_x3_pricing_structure():
    """
    Explain how the Sage X3 pricing structure works
    """
    print("=== Sage X3 Pricing Structure Explanation ===\n")
    
    print("The PRICSTRUCT table defines how discount/fee columns are interpreted:")
    print()
    
    print("INCDCR_0 to INCDCR_8 (Increment/Decrement):")
    print("  1 = Majoration (Fee/Charge) - adds to price")
    print("  2 = Minoration (Discount) - subtracts from price")  
    print("  0 = Not used")
    print()
    
    print("VALTYP_0 to VALTYP_8 (Value Type):")
    print("  1 = Montant (Fixed Amount) - direct monetary amount")
    print("  2 = Pourcentage Cumulé - percentage applied to running total")
    print("  3 = Pourcentage Cascade - percentage applied to original base")
    print("  0 = Not used")
    print()
    
    print("CLCRUL_0 to CLCRUL_8 (Calculation Rule/Base de Calcul):")
    print("  1 = Par Unité (Per Unit) - applied to unit price")
    print("  2 = Par Ligne (Per Line) - applied to line total")
    print("  3 = Par Document (Per Document) - applied to document total")
    print("  0 = Not used")
    print()
    
    print("Key Differences in Application:")
    print("• PAR UNITÉ: Adjustment affects unit price directly")
    print("  Example: 10€ fee per unit on 100 units = 10€ more per unit")
    print()
    print("• PAR LIGNE: Adjustment affects entire line total, then distributed")
    print("  Example: 100€ fee per line on 100 units = 1€ more per unit")
    print()
    print("• PAR DOCUMENT: Adjustment affects entire document total")
    print("  Example: 500€ fee per document spread across all lines")
    print()
    
    print("Example Calculation Flow:")
    print("Base Price: 100.00")
    print("Quantity: 50 units")
    print("Column 0: INCDCR=2, VALTYP=2, CLCRUL=1, Value=10 → 10% discount per unit")
    print("  → 100.00 - (100.00 × 10%) = 90.00 per unit")
    print("Column 1: INCDCR=2, VALTYP=2, CLCRUL=1, Value=5 → 5% cumulative discount")  
    print("  → 90.00 - (90.00 × 5%) = 85.50 per unit")
    print("Column 2: INCDCR=1, VALTYP=1, CLCRUL=2, Value=100 → 100€ fee per line")
    print("  → Line total: 85.50 × 50 = 4275.00")
    print("  → After fee: 4275.00 + 100.00 = 4375.00")
    print("  → New unit price: 4375.00 ÷ 50 = 87.50")
    print("Final Unit Price: 87.50")

def test_free_items_scenarios():
    """
    Test pour démontrer les différents scénarios de gratuités Sage X3
    """
    print("=== Test des Scénarios de Gratuités Sage X3 ===\n")
    
    # Créer des contextes de test
    base_context = PricingContext(
        customer_code="TEST001",
        item_code="PRODUCT_A",
        quantity=Decimal("20"),
        currency="EUR",
        unit_of_measure="UN"
    )
    
    # Test N pour M - Seuil
    print("Scénario 1: N pour M - Seuil")
    print("Règle: 'À partir de 10 achetés, 2 gratuits' (même article)")
    print(f"Commande: {base_context.quantity} unités de {base_context.item_code}")
    
    # Simulation manuelle du calcul
    focqtymin = Decimal('10')
    focqty = Decimal('2')
    if base_context.quantity >= focqtymin:
        print(f"✓ Seuil atteint ({base_context.quantity} ≥ {focqtymin})")
        print(f"→ Gratuité: {focqty} unités de {base_context.item_code}")
    else:
        print(f"✗ Seuil non atteint ({base_context.quantity} < {focqtymin})")
    print()
    
    # Test N pour M - Multiple  
    print("Scénario 2: N pour M - Multiple")
    print("Règle: 'Au-delà de 5 unités, 1 gratuit par tranche de 3'")
    print(f"Commande: {base_context.quantity} unités")
    
    focqtymin = Decimal('5')
    focqtybkt = Decimal('3') 
    focqty = Decimal('1')
    if base_context.quantity > focqtymin:
        excess_qty = base_context.quantity - focqtymin
        buckets = (excess_qty / focqtybkt).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        total_free = buckets * focqty
        print(f"✓ Excédent: {excess_qty} unités")
        print(f"✓ Tranches de {focqtybkt}: {buckets}")
        print(f"→ Gratuité: {total_free} unités")
    else:
        print(f"✗ Pas d'excédent")
    print()
    
    # Test Autre Article - Seuil
    print("Scénario 3: Autre Article - Seuil")
    print("Règle: 'À partir de 15 produits A, 1 produit B gratuit'")
    print(f"Commande: {base_context.quantity} unités de PRODUCT_A")
    
    focqtymin = Decimal('15')
    focitmref = "PRODUCT_B"
    focqty = Decimal('1')
    if base_context.quantity >= focqtymin:
        print(f"✓ Seuil atteint ({base_context.quantity} ≥ {focqtymin})")
        print(f"→ Gratuité: {focqty} unité de {focitmref}")
    else:
        print(f"✗ Seuil non atteint ({base_context.quantity} < {focqtymin})")
    print()
    
    # Test Total Commande - Montant
    print("Scénario 4: Total Commande - Montant")
    print("Règle: 'Si commande > 500€, 1 produit cadeau gratuit'")
    
    unit_price = Decimal('30.00')
    line_total = base_context.quantity * unit_price
    focamtmin = Decimal('500.00')
    focitmref = "CADEAU_SPECIAL"
    focqty = Decimal('1')
    
    print(f"Commande: {base_context.quantity} × {unit_price}€ = {line_total}€")
    if line_total >= focamtmin:
        print(f"✓ Seuil atteint ({line_total}€ ≥ {focamtmin}€)")
        print(f"→ Gratuité: {focqty} unité de {focitmref}")
    else:
        print(f"✗ Seuil non atteint ({line_total}€ < {focamtmin}€)")
    print()
    
    # Résumé des mécanismes
    print("=== Résumé des Mécanismes ===")
    print("FOCPRO (Type de gratuité):")
    print("  1 = N pour M (même article gratuit)")
    print("  2 = Autre Article (article différent gratuit)")  
    print("  3 = Total Commande (basé sur total commande)")
    print()
    print("FOCTYP (Mode d'attribution):")
    print("  1 = Seuil (une fois atteint)")
    print("  2 = Multiple (par tranches au-delà du seuil)")
    print()
    print("Seuils et tranches:")
    print("  FOCQTYMIN/FOCAMTMIN = Seuil minimum")
    print("  FOCQTYBKT/FOCAMTBKT = Taille des tranches (pour mode Multiple)")
    print("  FOCQTY = Quantité gratuite par déclenchement")

if __name__ == "__main__":
    # Example usage
    
    # Test des gratuités
    test_free_items_scenarios() 
    print("\n")
    
    # Test des types de calculs
    test_calculation_types()
    print("\n")
    
    # Explain the pricing structure first
    explain_sage_x3_pricing_structure()
    print("\n")
    
    # Run the complete test
    # test_pricing_engine_complete()