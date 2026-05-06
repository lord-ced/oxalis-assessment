with source as (
    select * from {{ source('raw', 'sales_raw') }}
),

cleaned as (
    select
        -- Transaction ID: convert empty string to NULL, preserve other NULLs
        case
            when transaction_id is null or trim(transaction_id) = '' then null
            else transaction_id
        end as transaction_id,
        
        -- Date: parse multiple formats with dayfirst=False, NULL on failure
        case
            when date is null or trim(date) = '' or lower(trim(date)) = 'na' then null
            -- ISO format: 2023-01-15, 2023/01/17, 2023-1-31
            when date ~ '^\d{4}[-/]\d{1,2}[-/]\d{1,2}$' then 
                to_date(date, 'YYYY-MM-DD')
            -- Slash format with smart day/month detection
            when date ~ '^\d{1,2}/\d{1,2}/\d{2,4}$' then 
                case
                    -- If first number > 12, must be DD/MM/YYYY
                    when cast(split_part(date, '/', 1) as integer) > 12 then
                        to_date(date, 'DD/MM/YYYY')
                    -- Otherwise assume MM/DD/YYYY (dayfirst=False default)
                    else
                        to_date(date, 'MM/DD/YYYY')
                end
            -- Dash format with smart day/month detection
            when date ~ '^\d{2}-\d{2}-\d{4}$' then 
                case
                    -- If second number > 12, format is MM-DD-YYYY
                    when cast(split_part(date, '-', 2) as integer) > 12 then
                        to_date(date, 'MM-DD-YYYY')
                    -- If first number > 12, format is DD-MM-YYYY
                    when cast(split_part(date, '-', 1) as integer) > 12 then
                        to_date(date, 'DD-MM-YYYY')
                    -- Ambiguous: default to DD-MM-YYYY (European convention)
                    else
                        to_date(date, 'DD-MM-YYYY')
                end
            -- European dot format: 29.01.2023, 6.2.2023
            when date ~ '^\d{1,2}\.\d{1,2}\.\d{4}$' then 
                to_date(date, 'DD.MM.YYYY')
            -- Month name format: 26-Jan-23, 01-Mar-23
            when date ~ '^\d{1,2}-[A-Za-z]{3}-\d{2}$' then 
                to_date(date, 'DD-Mon-YY')
            else null
        end as date,
        
        -- Store ID: extract trailing digits, prefix with STORE_
        'STORE_' || regexp_replace(trim(store_id), '.*?(\d+)$', '\1') as store_id,
        
        -- Region: uppercase, replace internal spaces with underscore
        upper(replace(trim(region), ' ', '_')) as region,
        
        -- Product category: trim, preserve casing
        trim(product_category) as product_category,
        
        -- Quantity sold: cast to integer, NULL stays NULL
        case
            when quantity_sold is null or trim(quantity_sold) = '' or lower(trim(quantity_sold)) = 'na' then null
            else cast(quantity_sold as integer)
        end as quantity_sold,
        
        -- Unit price: strip $, cast to numeric
        case
            when unit_price is null or trim(unit_price) = '' or lower(trim(unit_price)) in ('na', 'error') then null
            else cast(regexp_replace(trim(unit_price), '^\$', '') as numeric)
        end as unit_price,
        
        -- Discount: normalize to decimal [0,1]
        case
            when discount is null or trim(discount) = '' or lower(trim(discount)) = 'na' then null
            when regexp_replace(trim(discount), '%', '') ~ '^\d+\.?\d*$' then
                case
                    when cast(regexp_replace(trim(discount), '%', '') as numeric) <= 1 
                        then cast(regexp_replace(trim(discount), '%', '') as numeric)
                    else cast(regexp_replace(trim(discount), '%', '') as numeric) / 100
                end
            else null
        end as discount,
        
        -- Customer type: map RegularCustomer, keep Premier/Premium distinct
        case
            when lower(trim(customer_type)) = 'regularcustomer' then 'Regular'
            when trim(customer_type) is not null and trim(customer_type) != '' 
                then trim(customer_type)
            else null
        end as customer_type,
        
        -- Payment method: map Debit to Debit Card, preserve NULLs
        case
            when lower(trim(payment_method)) = 'debit' then 'Debit Card'
            when trim(payment_method) is not null and trim(payment_method) != '' 
                then trim(payment_method)
            else null
        end as payment_method
        
    from source
)

select * from cleaned