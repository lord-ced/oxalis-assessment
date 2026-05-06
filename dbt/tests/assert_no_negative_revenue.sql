-- Flag any rows where net_revenue is negative
-- This catches data quality issues where discounts exceed 100% or prices are negative

select
    transaction_id,
    date,
    store_id,
    quantity_sold,
    unit_price,
    discount,
    net_revenue
from {{ ref('int_sales_enriched') }}
where net_revenue < 0